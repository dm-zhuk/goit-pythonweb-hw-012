import pytest
import pytest_asyncio
from unittest.mock import patch
from fastapi import UploadFile
from io import BytesIO
from src.services.cloudinary_config import UploadFileService


@pytest_asyncio.fixture(scope="function")
def fake_upload_file():
    file_content = b"fake image bytes"
    file = UploadFile(filename="test.png", file=BytesIO(file_content))
    return file


@patch("cloudinary.uploader.upload")
@patch("cloudinary.CloudinaryImage.build_url")
def test_upload_file_success(mock_build_url, mock_upload, fake_upload_file):
    mock_upload.return_value = {"version": 123456}
    mock_build_url.return_value = "http://res.cloudinary.com/fake_image_url"

    service = UploadFileService("cloud_name", "api_key", "api_secret")
    result = service.upload_file(fake_upload_file, "testuser")

    mock_upload.assert_called_once_with(
        fake_upload_file.file, public_id="RestApp/testuser", overwrite=True
    )
    mock_build_url.assert_called_once_with(
        width=250, height=250, crop="fill", version=123456
    )

    assert result == "http://res.cloudinary.com/fake_image_url"


@patch("cloudinary.uploader.upload", side_effect=Exception("Upload failed"))
def test_upload_file_raises_exception(mock_upload, fake_upload_file):
    service = UploadFileService("cloud_name", "api_key", "api_secret")

    with pytest.raises(Exception) as exc_info:
        service.upload_file(fake_upload_file, "testuser")

    assert "Failed to upload file" in str(exc_info.value)
