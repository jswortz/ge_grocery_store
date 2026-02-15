"""Product image generation tool.

Wraps Vertex AI's Imagen API to generate product imagery grounded
in brand guidelines. Uses a FunctionTool for ADK integration.

NOTE: This tool requires the Vertex AI Imagen API to be enabled.
Image generation capabilities depend on model availability in the
configured region. Gemini 2.0 Flash native image generation is
an alternative if Imagen is not available.
"""

import base64
import logging

logger = logging.getLogger(__name__)


def _load_config():
    from ..agent import _load_config as _agent_load_config
    return _agent_load_config()


def generate_product_image(
    product_name: str,
    style_description: str = "professional product photography, bright natural lighting, clean background",
    brand_colors: str = "green (#2e7d32) and white, with gold (#f9a825) accents",
) -> dict:
    """Generate a product image based on brand guidelines.

    Args:
        product_name: Name of the product (e.g., "Nano Banana Pro Bar").
        style_description: Visual style instructions for the image.
        brand_colors: Brand color palette to incorporate.

    Returns:
        Dict with 'status', 'message', and optionally 'image_base64' and 'mime_type'.
    """
    config = _load_config()
    project_id = config["project"]["id"]
    retailer = config["retailer"]["name"]
    imagen_model = config.get("models", {}).get("imagen", "imagen-3.0-generate-002")

    prompt = (
        f"Professional product photo of '{product_name}' for {retailer} grocery store. "
        f"Style: {style_description}. "
        f"Brand colors: {brand_colors}. "
        f"The product should look appetizing and premium. "
        f"Clean, well-lit composition suitable for a promotional flyer or website."
    )

    try:
        from google.cloud import aiplatform
        from vertexai.preview.vision_models import ImageGenerationModel

        aiplatform.init(project=project_id, location="us-central1")
        model = ImageGenerationModel.from_pretrained(imagen_model)
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_few",
        )

        if response.images:
            image = response.images[0]
            image_bytes = image._image_bytes

            # Save to GCS instead of returning base64 inline to avoid
            # bloating session history (a single image is ~400K-1.5M tokens
            # as base64, which causes context overflow on subsequent turns).
            import hashlib
            from google.cloud import storage

            blob_name = (
                f"generated_images/{product_name.lower().replace(' ', '_')}_"
                f"{hashlib.md5(image_bytes[:1024]).hexdigest()[:8]}.png"
            )
            gcs_bucket = config.get("gcs", {}).get(
                "bucket", f"{project_id}-ge-workshop"
            )
            try:
                storage_client = storage.Client(project=project_id)
                bucket = storage_client.bucket(gcs_bucket)
                blob = bucket.blob(blob_name)
                blob.upload_from_string(image_bytes, content_type="image/png")
                image_uri = f"gs://{gcs_bucket}/{blob_name}"
                return {
                    "status": "success",
                    "message": f"Generated product image for '{product_name}'",
                    "image_uri": image_uri,
                    "mime_type": "image/png",
                    "size_bytes": len(image_bytes),
                }
            except Exception as gcs_err:
                logger.warning("GCS upload failed (%s), returning base64", gcs_err)
                return {
                    "status": "success",
                    "message": f"Generated product image for '{product_name}'",
                    "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                    "mime_type": "image/png",
                }
        else:
            return {
                "status": "no_images",
                "message": "Image generation returned no results. Try adjusting the prompt.",
            }

    except ImportError:
        logger.warning("Vertex AI SDK not available; returning placeholder")
        return {
            "status": "placeholder",
            "message": (
                f"Image generation SDK not available. "
                f"Prompt that would be used: {prompt}"
            ),
        }
    except Exception as e:
        logger.error("Image generation failed: %s", e)
        return {
            "status": "error",
            "message": f"Image generation failed: {str(e)}",
        }


def create_image_gen_tool():
    """Create a FunctionTool for product image generation."""
    from google.adk.tools import FunctionTool

    return FunctionTool(func=generate_product_image)
