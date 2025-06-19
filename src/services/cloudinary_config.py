import cloudinary
import cloudinary.uploader
from fastapi import UploadFile


class UploadFileService:
    def __init__(self, cloud_name, api_key, api_secret):
        """
        Initialize the UploadFileService with Cloudinary configuration.

        Args:
            cloud_name: The Cloudinary cloud name.
            api_key: The Cloudinary API key.
            api_secret: The Cloudinary API secret.
        """

        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    def upload_file(self, file: UploadFile, username: str) -> str:
        """
        Uploads a file to Cloudinary and returns the URL of the uploaded image.

        The image is uploaded with a public ID in the format "RestApp/<username>".
        If an image with this public ID already exists, it is overwritten.
        The image is resized to 250x250px and cropped to fill the dimensions.

        Args:
            file: The file to upload.
            username: The username of the user to associate with the image.

        Returns:
            The URL of the uploaded image.

        Raises:
            Exception: If the upload fails.
        """
        public_id = f"RestApp/{username}"
        try:
            r = cloudinary.uploader.upload(
                file.file, public_id=public_id, overwrite=True
            )
            src_url = cloudinary.CloudinaryImage(public_id).build_url(
                width=250, height=250, crop="fill", version=r.get("version")
            )
            return src_url
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}")
