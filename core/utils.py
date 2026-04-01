import threading
import time
import re
import httpx
from cache_utils import cached, cleanup_cache
from database import SessionLocal

def extract_category_from_text(title: str, description: str = "", platform: str = "") -> str:
    """Extract category from job title and description using keyword matching"""
    text = f"{title} {description}".lower()
    
    # Define category keywords
    categories = {
        "Web Development": [
            "website", "web", "html", "css", "javascript", "react", "vue", "angular", "node", "php", 
            "wordpress", "shopify", "ecommerce", "frontend", "backend", "fullstack", "django", "flask",
            "laravel", "codeigniter", "bootstrap", "jquery", "ajax", "api", "rest", "graphql", "web development"
        ],
        "Mobile Development": [
            "mobile", "app", "ios", "android", "flutter", "react native", "swift", "kotlin", 
            "xamarin", "cordova", "phonegap", "ionic", "mobile app"
        ],
        "Data Science & Analytics": [
            "data", "analytics", "machine learning", "ai", "python", "sql", "tableau", 
            "power bi", "statistics", "analysis", "visualization", "pandas", "numpy", "scikit"
        ],
        "Design & Creative": [
            "design", "logo", "graphic", "ui", "ux", "photoshop", "illustrator", "figma", "sketch",
            "branding", "creative", "visual", "banner", "poster", "flyer", "mockup"
        ],
        "Writing & Content": [
            "writing", "content", "copywriting", "blog", "article", "seo", "marketing", "social media",
            "content creation", "proofreading", "editing", "technical writing"
        ],
        "Digital Marketing": [
            "marketing", "seo", "sem", "ppc", "google ads", "facebook ads", "social media marketing",
            "email marketing", "affiliate", "influencer", "campaign", "lead generation", "optimization",
            "adwords", "facebook marketing", "instagram marketing"
        ],
        "Video & Animation": [
            "video", "animation", "editing", "motion graphics", "after effects", "premiere", 
            "3d", "modeling", "rendering", "explainer video", "explainer", "youtube", "video editing"
        ],
        "Translation & Languages": [
            "translation", "translate", "language", "localization", "interpreter", "multilingual",
            "spanish", "french", "german", "chinese", "japanese", "arabic"
        ],
        "Business & Consulting": [
            "business", "consulting", "strategy", "plan", "market research", "financial", 
            "accounting", "bookkeeping", "virtual assistant", "admin", "project management"
        ],
        "Engineering & Architecture": [
            "engineering", "cad", "autocad", "solidworks", "architecture", "structural", 
            "mechanical", "electrical", "civil", "3d modeling", "blueprint"
        ]
    }
    
    # Count matches for each category with priority weighting
    category_scores = {}
    for category, keywords in categories.items():
        score = 0
        for keyword in keywords:
            # Use word boundaries for single-letter keywords or add them back with specific context
            if keyword == "r" and " r " in text:  # R programming language
                score += 2
            elif len(keyword) == 1:  # Skip other single letters
                continue
            elif keyword in text:
                # Give higher weight to more specific keywords
                if len(keyword.split()) > 1:  # Multi-word keywords get higher priority
                    score += 2
                elif keyword in ["seo", "optimization", "marketing", "ads", "campaign"]:
                    # Marketing-specific keywords get priority for Digital Marketing
                    if category == "Digital Marketing":
                        score += 3
                    else:
                        score += 1
                else:
                    score += 1
        
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or try platform-specific extraction
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    # Fallback: try to extract from platform-specific patterns
    if platform.lower() == "upwork":
        # Upwork sometimes has category info in URLs or descriptions
        if "web-mobile-software-dev" in text:
            return "Web Development"
        elif "design-creative" in text:
            return "Design & Creative"
        elif "writing" in text:
            return "Writing & Content"
    
    # Final check: if text is very short or empty, return Uncategorized
    if len(text.strip()) < 10:
        return "Uncategorized"
    
    return "Uncategorized"

def start_cache_cleanup():
    """Start periodic cache cleanup"""
    def cleanup_task():
        while True:
            try:
                cleanup_cache()
                time.sleep(300)  # Clean up every 5 minutes
            except Exception as e:
                print(f"Cache cleanup error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()

def extract_category_from_url(url: str, platform: str) -> str:
    """Extract category from project URL based on platform"""
    if not url:
        return "Uncategorized"
    
    try:
        if platform.lower() == "freelancer":
            # Freelancer URL format: https://www.freelancer.com/projects/{category}/{title-slug}
            match = re.search(r'/projects/([^/]+)/', url)
            if match:
                category = match.group(1)
                # Convert URL-friendly category to readable format
                category = category.replace('-', ' ').title()
                return category
        
        elif platform.lower() == "upwork":
            # Upwork URLs might have different patterns, add logic here if needed
            # For now, try to extract from URL structure if available
            pass
        
        return "Uncategorized"
    
    except Exception as e:
        print(f"Error extracting category from URL {url}: {e}")
        return "Uncategorized"

def init_db():
    try:
        from database import engine, Base
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

async def trigger_webhook_async(webhook_url: str, payload: dict, headers: dict):
    """Async webhook trigger with shorter timeout and better error handling"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:  # Reduced from 600s to 30s
            response = await client.post(webhook_url, json=payload, headers=headers)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_text": response.text[:500] if response.text else 'empty'
            }
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timeout", "status_code": 504}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": 500}

@cached(ttl=30, key_prefix="health_")  # Cache for 30 seconds
def _check_db_status():
    """Cached database status check optimized for transaction pooler"""
    try:
        from db_utils import quick_db_check
        if quick_db_check():
            return "connected"
        else:
            return "disconnected"
    except Exception as e:
        return f"error: {str(e)[:50]}"
