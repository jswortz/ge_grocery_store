"""Product image generation tool.

Wraps Vertex AI's Gemini image generation to create product imagery
grounded in brand guidelines. Uses a FunctionTool for ADK integration.

Uses gemini-3.1-flash-image-preview (Nano Banana 2) for image generation.
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
        Dict with 'status', 'message', and optionally 'image_uri' or 'image_base64'.
    """
    config = _load_config()
    project_id = config["project"]["id"]
    retailer = config["retailer"]["name"]
    imagen_model = config.get("models", {}).get("imagen", "gemini-3.1-flash-image-preview")

    prompt = (
        f"Professional product photo of '{product_name}' for {retailer} grocery store. "
        f"Style: {style_description}. "
        f"Brand colors: {brand_colors}. "
        f"The product should look appetizing and premium. "
        f"Clean, well-lit composition suitable for a promotional flyer or website."
    )

    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        # Image generation models require the global endpoint
        vertexai.init(project=project_id, location="global")
        model = GenerativeModel(imagen_model)
        response = model.generate_content(
            prompt,
            generation_config={
                "response_modalities": ["IMAGE", "TEXT"],
            },
        )

        # Extract image from response parts
        image_bytes = None
        mime_type = "image/png"
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/png"
                break

        if image_bytes:
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
                blob.upload_from_string(image_bytes, content_type=mime_type)
                image_uri = f"gs://{gcs_bucket}/{blob_name}"

                # Use proxy URL for frontend display (avoids signed URL /
                # CORS issues when running with ADC instead of service account keys).
                # The frontend server proxies /api/images/<path> to GCS.
                proxy_url = f"/api/images/{blob_name}"

                return {
                    "status": "success",
                    "message": (
                        f"Generated product image for '{product_name}'.\n\n"
                        f"![{product_name}]({proxy_url})"
                    ),
                    "image_uri": image_uri,
                    "image_url": proxy_url,
                    "mime_type": mime_type,
                    "size_bytes": len(image_bytes),
                }
            except Exception as gcs_err:
                logger.warning("GCS upload failed (%s), returning base64", gcs_err)
                return {
                    "status": "success",
                    "message": f"Generated product image for '{product_name}'",
                    "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                    "mime_type": mime_type,
                }
        else:
            return {
                "status": "no_images",
                "message": "Image generation returned no image data. Try adjusting the prompt.",
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
