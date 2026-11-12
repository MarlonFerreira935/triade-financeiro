"""Validation, image preparation and storage for receipt files."""
import asyncio
import io
import logging
import math
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from ai_service import extract_receipt
from finance import ACCOUNT_MAP
from storage_service import get_object, put_object

MAX_BYTES = 10 * 1024 * 1024
MONTH_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
MIME_TYPES = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'pdf': 'application/pdf'}
IMAGE_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceiptFile:
    filename: str
    extension: str
    content_type: str
    content: bytes
    image_content: bytes | None = None


def prepare_image(content):
    try:
        with Image.open(io.BytesIO(content)) as image:
            mime = IMAGE_FORMATS.get(image.format)
            if not mime:
                raise ValueError('Unsupported image format')
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            image.seek(0)
            image.thumbnail((1800, 1800))
            output = io.BytesIO()
            image.convert('RGB').save(output, format='JPEG', quality=90)
            return mime, output.getvalue()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(400, 'Imagem inválida.') from exc


async def read_receipt_upload(upload):
    content = await upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, 'O arquivo deve ter até 10 MB.')
    filename = upload.filename or ''
    extension = filename.rsplit('.', 1)[-1].lower()
    if extension not in MIME_TYPES:
        raise HTTPException(400, 'Envie JPG, PNG, WEBP ou PDF.')
    if extension == 'pdf':
        if not content.startswith(b'%PDF'):
            raise HTTPException(400, 'PDF inválido.')
        return ReceiptFile(filename, extension, MIME_TYPES[extension], content)
    mime, image_content = await run_in_threadpool(prepare_image, content)
    if mime != MIME_TYPES[extension]:
        raise HTTPException(400, 'O formato da imagem não corresponde à extensão do arquivo.')
    return ReceiptFile(filename, extension, mime, content, image_content)


async def extract_fields(receipt_file):
    if receipt_file.image_content is None:
        return {}, 'PDF salvo. Preencha os dados para vincular ao lançamento.'
    try:
        extracted = await asyncio.wait_for(extract_receipt(receipt_file.image_content), timeout=75)
        if not isinstance(extracted, dict):
            raise ValueError('Invalid extraction result')
        return extracted, None
    except Exception:
        logger.exception('Falha na leitura de comprovante')
        return {}, 'Arquivo salvo. A leitura automática não foi concluída; confira e preencha os campos.'


def receipt_date(value, month):
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        if MONTH_PATTERN.fullmatch(month):
            try:
                return date.fromisoformat(f'{month}-01').isoformat()
            except ValueError:
                pass
        return date.today().isoformat()


def normalize_fields(fields, filename, month):
    account_id = str(fields.get('account_id', '50'))
    account = ACCOUNT_MAP.get(account_id, ACCOUNT_MAP['50'])
    amount = fields.get('amount')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        amount = None
    elif not math.isfinite(amount) or not 0 < amount <= 100000000:
        amount = None
    return {'description': str(fields.get('description') or filename)[:250],
            'amount': amount, 'date': receipt_date(fields.get('date'), month),
            'account_id': account['id'], 'type': account['type'],
            'note': str(fields.get('note') or '')[:2000]}


async def store_receipt(db, upload, month):
    receipt_file = await read_receipt_upload(upload)
    receipt_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    path = f'triade-poa/receipts/{now:%Y-%m}/{receipt_id}.{receipt_file.extension}'
    try:
        stored = await run_in_threadpool(put_object, path, receipt_file.content, receipt_file.content_type)
    except Exception as exc:
        logger.exception('Falha ao guardar comprovante')
        raise HTTPException(503, 'Não foi possível armazenar o arquivo. Tente novamente.') from exc
    fields, warning = await extract_fields(receipt_file)
    extraction = normalize_fields(fields, receipt_file.filename, month)
    record = {'id': receipt_id, 'filename': receipt_file.filename, 'storage_path': stored['path'],
              'content_type': receipt_file.content_type, 'size': len(receipt_file.content),
              'date': extraction['date'], 'category': ACCOUNT_MAP[extraction['account_id']]['group'],
              'amount': extraction['amount'], 'status': 'pendente', 'transaction_id': None,
              'is_deleted': False, 'created_at': now.isoformat(), 'extraction': extraction, 'warning': warning}
    await db.receipts.insert_one(record.copy())
    return {key: value for key, value in record.items() if key != 'storage_path'}


async def find_receipt(db, receipt_id):
    record = await db.receipts.find_one({'id': receipt_id, 'is_deleted': False}, {'_id': 0})
    if not record:
        raise HTTPException(404, 'Comprovante não encontrado.')
    return record


async def receipt_bytes(record):
    """Return bytes or raise: no unassigned response variable or empty success response."""
    try:
        content = await run_in_threadpool(get_object, record['storage_path'])
        if not isinstance(content, bytes):
            raise TypeError('Storage returned invalid content')
        return content
    except Exception as exc:
        raise HTTPException(503, 'Não foi possível baixar o comprovante agora.') from exc