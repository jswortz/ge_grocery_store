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
        model = ImageGenerationModel.from_pretrained("imagegeneration@006")
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_few",
        )

        if response.images:
            image = response.images[0]
            image_bytes = image._image_bytes
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
