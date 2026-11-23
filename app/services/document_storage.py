
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


CHUNK_SIZE = 1024 * 1024


async def save_document(
    file: UploadFile,
    upload_dir: Path,
) -> tuple[str, int]:

    # Create the storage directory if it doesn't exist.
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Preserve only the validated file extension.
    extension = Path(file.filename).suffix.lower()

    # Generate a unique storage filename.
    stored_filename = f"{uuid4().hex}{extension}"

    # Construct the destination path.
    destination = upload_dir / stored_filename

    total_size = 0

    # Start reading from the beginning.
    await file.seek(0)

    try:
        # "xb" creates a new file and refuses to overwrite an existing one.
        with destination.open("xb") as output:

            while chunk := await file.read(CHUNK_SIZE):
                output.write(chunk)
                total_size += len(chunk)

    except Exception:
        # Remove an incomplete file if storage fails.
        destination.unlink(missing_ok=True)
        raise

    finally:
        # Reset the uploaded file pointer.
        await file.seek(0)

    return stored_filename, total_size
