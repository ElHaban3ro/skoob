import os
import boto3
from dotenv import load_dotenv

load_dotenv()

STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
LOCAL_UPLOAD_DIR = os.getenv("LOCAL_UPLOAD_DIR", "content/books")
S3_BUCKET = os.getenv("S3_BUCKET")

if STORAGE_TYPE == "local" and not os.path.exists(LOCAL_UPLOAD_DIR):
    os.makedirs(LOCAL_UPLOAD_DIR)

def save_file(file, filename):
    if STORAGE_TYPE == "local":
        filepath = os.path.join(LOCAL_UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            buffer.write(file.read())
        return filepath
    elif STORAGE_TYPE == "s3":
        s3 = boto3.client("s3")
        s3.upload_fileobj(file, S3_BUCKET, filename)
        return f"s3://{S3_BUCKET}/{filename}"

def generate_share_link(filename, expires=3600):
    if STORAGE_TYPE == "local":
        return f"/pdfs/download/{filename}"
    elif STORAGE_TYPE == "s3":
        s3 = boto3.client("s3")
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": filename},
            ExpiresIn=expires
        )
        return url
