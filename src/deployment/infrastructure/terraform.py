
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TerraformGenerator:
    """
    Generates Terraform templates for infrastructure provisioning.
    """

    def generate_templates(self, output_path: Path, provider: str = "aws"):
        """
        Generate main.tf and variables.tf.
        """
        tf_dir = output_path / "terraform"
        tf_dir.mkdir(parents=True, exist_ok=True)

        if provider == "aws":
            self._generate_aws_templates(tf_dir)

        logger.info(f"Generated Terraform templates in {tf_dir}")

    def _generate_aws_templates(self, tf_dir: Path):
        main_tf = """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "assets" {
  bucket_prefix = "app-assets-"
}
"""
        with open(tf_dir / "main.tf", "w") as f:
            f.write(main_tf)
