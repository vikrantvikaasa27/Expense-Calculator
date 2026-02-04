"""Vision service using Google Gemini for bill extraction."""

import json
import re
from decimal import Decimal
from io import BytesIO

import google.generativeai as genai
from PIL import Image

from app.config import settings
from app.schemas.expense import BillExtractionResult


class VisionService:
    """Service for extracting expense data from bill images using Gemini Vision."""
    
    def __init__(self):
        """Initialize Gemini client."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def extract_from_bill(self, image_bytes: bytes) -> BillExtractionResult:
        """
        Extract expense information from a bill image.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            BillExtractionResult with extracted data
        """
        try:
            # Load image
            image = Image.open(BytesIO(image_bytes))
            
            # Prompt for structured extraction
            prompt = """Analyze this receipt/bill image and extract the following information.
Return ONLY a valid JSON object with these fields:
{
    "total_amount": <number or null if not found>,
    "merchant_name": "<store/restaurant name or null>",
    "suggested_category": "<one of: Food & Dining, Transportation, Groceries, Utilities, Entertainment, Healthcare, Shopping, Education, Travel, Others>",
    "confidence": <0.0 to 1.0 based on image clarity and extraction confidence>
}

Important:
- For total_amount, look for "Total", "Grand Total", "Amount Due", etc.
- Extract the final amount including taxes
- If multiple totals exist, use the largest one (final total)
- Be accurate with the decimal places"""

            # Call Gemini Vision
            response = self.model.generate_content([prompt, image])
            response_text = response.text.strip()
            
            # Parse JSON from response
            # Handle markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(response_text)
            
            return BillExtractionResult(
                amount=Decimal(str(data.get("total_amount"))) if data.get("total_amount") else None,
                merchant_name=data.get("merchant_name"),
                suggested_category=data.get("suggested_category"),
                confidence=float(data.get("confidence", 0.5)),
            )
            
        except json.JSONDecodeError as e:
            # Try to extract amount using regex as fallback
            amount = self._extract_amount_fallback(response_text if 'response_text' in dir() else "")
            return BillExtractionResult(
                amount=amount,
                confidence=0.3,
                raw_text=str(e),
            )
        except Exception as e:
            return BillExtractionResult(
                confidence=0.0,
                raw_text=f"Error: {str(e)}",
            )
    
    def _extract_amount_fallback(self, text: str) -> Decimal | None:
        """Fallback regex extraction for amounts."""
        # Look for currency patterns
        patterns = [
            r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:\$|USD)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'total[:\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                return Decimal(amount_str)
        
        return None


# Singleton instance
vision_service = VisionService()
