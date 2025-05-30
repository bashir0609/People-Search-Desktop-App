import pandas as pd
import openai
import time
import requests
from typing import Optional, Dict, Any, List
import json
import re
import os
from dotenv import load_dotenv
import logging
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CEOFinder:
    def __init__(self, api_keys: Dict[str, str]):
        """Initialize with API keys - optimized for maximum CEO finding success"""
        self.api_keys = api_keys
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Rate limiting
        self.last_api_call = {}
        self.rate_limit_lock = threading.Lock()
        
        # Initialize OpenAI
        if 'openai' in api_keys:
            try:
                self.openai_client = openai.OpenAI(api_key=api_keys['openai'])
                self.use_new_openai_api = True
                print("✓ OpenAI API initialized")
            except AttributeError:
                openai.api_key = api_keys['openai']
                self.use_new_openai_api = False
                print("✓ OpenAI API initialized")
        
        # Initialize Anthropic (Claude) if available
        self.anthropic_client = None
        if 'anthropic' in api_keys:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=api_keys['anthropic'])
                print("✓ Anthropic (Claude) API initialized")
            except ImportError:
                pass  # Silent fail
            except Exception as e:
                pass  # Silent fail
        
        # Initialize Google Custom Search if available
        self.google_search_client = None
        self.google_search_engine_id = None
        if 'google_search' in api_keys and 'google_search_cx' in api_keys:
            self.google_search_client = api_keys['google_search']
            self.google_search_engine_id = api_keys['google_search_cx']
            print("✓ Google Custom Search API initialized")
        
        # Initialize Gemini
        self.gemini_client = None
        if 'gemini' in api_keys:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_keys['gemini'])
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
                print("✓ Google Gemini API initialized")
            except Exception as e:
                pass  # Silent fail
        
        # Contact database APIs (expanded)
        self.contact_apis = {
            'hunter': api_keys.get('hunter'),
            'apollo': api_keys.get('apollo'),
            'clearbit': api_keys.get('clearbit'),
            'rocketreach': api_keys.get('rocketreach'),
        }
        
        active_apis = len([k for k in api_keys.values() if k])
        print(f"✓ Loaded {active_apis} API keys")  # Keep essential startup info
    
    def _rate_limit(self, api_name: str, min_interval: float = 1.0):
        """Rate limiting"""
        with self.rate_limit_lock:
            now = time.time()
            last_call = self.last_api_call.get(api_name, 0)
            time_since_last = now - last_call
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_api_call[api_name] = time.time()
    
    def get_aggressive_website_content(self, url: str, company_name: str) -> str:
        """Aggressively extract ANY content that might contain CEO info with robust SSL handling"""
        try:
            # Only show essential progress - no detailed scraping logs
            print(f"    📄 Extracting website content...")
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            self._rate_limit('web_scraping', 0.3)
            
            # Try multiple approaches for SSL/connection issues
            success = False
            content = ""
            
            # Method 1: Try with default SSL settings
            try:
                response = self.session.get(url, timeout=12, allow_redirects=True, verify=True)
                response.raise_for_status()
                content = response.text
                success = True
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                pass  # Try next method
            
            # Method 2: Try with relaxed SSL verification
            if not success:
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    response = self.session.get(url, timeout=12, allow_redirects=True, verify=False)
                    response.raise_for_status()
                    content = response.text
                    success = True
                except Exception:
                    pass  # Try next method
            
            # Method 3: Try HTTP instead of HTTPS
            if not success and url.startswith('https://'):
                try:
                    http_url = url.replace('https://', 'http://')
                    response = self.session.get(http_url, timeout=12, allow_redirects=True)
                    response.raise_for_status()
                    content = response.text
                    success = True
                except Exception:
                    pass  # Try next method
            
            # Method 4: Try with different user agent
            if not success:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; CEOFinder/1.0; +http://example.com/bot)'
                    }
                    response = requests.get(url, headers=headers, timeout=10, verify=False)
                    response.raise_for_status()
                    content = response.text
                    success = True
                except Exception:
                    pass
            
            if not success:
                return ""
            
            # Process content quietly
            content = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Look for leadership terms
            leadership_sentences = []
            sentences = content.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:
                    if any(term in sentence.lower() for term in [
                        'ceo', 'chief executive', 'president', 'founder', 'owner', 
                        'director', 'manager', 'leader', 'head of', 'chairman',
                        'co-founder', 'managing', 'executive', company_name.lower(),
                        'established', 'started', 'founded', 'created', 'built'
                    ]):
                        leadership_sentences.append(sentence)
            
            if leadership_sentences:
                result = '. '.join(leadership_sentences[:20])
                print(f"    ✓ Found leadership content")
                return result[:8000]
            else:
                print(f"    ℹ️ Using general content")
                return content[:8000]
                
        except Exception as e:
            # Only log if it's a real error, not just failed connection
            return ""
    
    def search_with_google_custom_search(self, company_name: str) -> str:
        """Use Google Custom Search API for high-quality CEO search"""
        if not self.google_search_client or not self.google_search_engine_id:
            return ""
        
        search_queries = [
            f"{company_name} CEO chief executive officer",
            f"{company_name} founder president owner",
            f'"{company_name}" leadership executive team'
        ]
        
        all_results = []
        
        for query in search_queries[:2]:  # Limit to avoid quota usage
            try:
                self._rate_limit('google_search', 1.0)
                
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_search_client,
                    'cx': self.google_search_engine_id,
                    'q': query,
                    'num': 5
                }
                
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'items' in data:
                        for item in data['items']:
                            title = item.get('title', '')
                            snippet = item.get('snippet', '')
                            combined = f"{title} {snippet}"
                            if len(combined) > 30:
                                all_results.append(combined)
                
            except Exception as e:
                continue
        
        if all_results:
            combined = " | ".join(all_results[:8])
            return combined[:4000]
        else:
            return ""
    
    def find_ceo_with_anthropic(self, company_name: str, website_url: str = None, linkedin_url: str = None) -> Dict[str, Any]:
        """Use Anthropic Claude for CEO finding"""
        if not self.anthropic_client:
            return self._no_result("Anthropic not available")
        
        try:
            self._rate_limit('anthropic', 1.0)
            
            # Build context with all available info
            context_parts = [f"Company: {company_name}"]
            
            # Add Google Custom Search results
            google_results = self.search_with_google_custom_search(company_name)
            if google_results:
                context_parts.append(f"Google search results: {google_results}")
            
            # Add website content
            if website_url:
                website_content = self.get_aggressive_website_content(website_url, company_name)
                if website_content:
                    context_parts.append(f"Website content: {website_content}")
            
            if linkedin_url:
                context_parts.append(f"LinkedIn: {linkedin_url}")
            
            context = "\n\n".join(context_parts)
            
            prompt = f"""You are an expert business researcher. Find ANY person associated with {company_name} leadership.

RESEARCH DATA:
{context}

TASK: Extract ANY person's name who might be a leader of {company_name}.

Look for:
- CEO, Chief Executive Officer, President, Founder, Co-founder, Owner
- Director, Manager, Chairman, Executive, Leader
- Anyone who "founded", "started", "created", "owns", "leads", "manages" the company
- Any person mentioned in company leadership context

INSTRUCTIONS:
- Be VERY generous - extract any name that might be a leader
- Even if not explicitly called "CEO", include them if they seem to lead the company
- Include founders, owners, presidents - not just CEOs
- If you find multiple names, pick the most senior one
- Extract the name even with low confidence

Return ONLY this JSON format:
{{
    "ceo_name": "Person's full name (First Last)",
    "ceo_title": "Their role/title",
    "confidence": "high/medium/low",
    "source": "Anthropic Claude analysis",
    "additional_info": "How/where you found this name"
}}

Find any leadership name you can:"""

            message = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Fastest/cheapest Claude model
                max_tokens=300,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = message.content[0].text.strip()
            return self._super_aggressive_parse(result_text, "Anthropic Claude", context)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._error_result("Anthropic error", str(e))
    
    def try_apollo_api(self, company_name: str, website_url: str = None) -> Dict[str, Any]:
        """Apollo.io API for finding company leadership"""
        if not self.contact_apis.get('apollo'):
            return self._no_result("Apollo API not available")
        
        try:
            self._rate_limit('apollo', 2.0)
            
            url = "https://api.apollo.io/v1/mixed_people/search"
            
            headers = {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json',
                'X-Api-Key': self.contact_apis['apollo']
            }
            
            payload = {
                "q_organization_name": company_name,
                "page": 1,
                "per_page": 10,
                "person_titles": ["CEO", "Chief Executive Officer", "President", "Founder", "Co-Founder", "Owner", "Managing Director"]
            }
            
            response = self.session.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                if 'people' in data and data['people']:
                    person = data['people'][0]  # Get first result
                    return {
                        "ceo_name": person.get('name', 'Not found'),
                        "ceo_title": person.get('title', 'CEO'),
                        "ceo_email": person.get('email', ''),
                        "ceo_linkedin": person.get('linkedin_url', ''),
                        "confidence": "high",
                        "source": "Apollo.io"
                    }
            
            return self._no_result("Apollo API - no CEO found")
            
        except Exception as e:
            logger.error(f"Apollo API error: {e}")
            return self._error_result("Apollo API error", str(e))
    
    def try_rocketreach_api(self, company_name: str, website_url: str = None) -> Dict[str, Any]:
        """RocketReach API for contact information"""
        if not self.contact_apis.get('rocketreach'):
            return self._no_result("RocketReach API not available")
        
        try:
            self._rate_limit('rocketreach', 2.0)
            
            url = "https://api.rocketreach.co/v2/api/search"
            headers = {'Api-Key': self.contact_apis['rocketreach']}
            
            params = {
                'query': f"{company_name} CEO",
                'start': 0,
                'size': 10
            }
            
            response = self.session.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                if 'profiles' in data and data['profiles']:
                    for profile in data['profiles']:
                        title = profile.get('current_title', '').lower()
                        if any(ceo_term in title for ceo_term in ['ceo', 'chief executive', 'president', 'founder', 'owner']):
                            return {
                                "ceo_name": profile.get('name', 'Not found'),
                                "ceo_title": profile.get('current_title', 'CEO'),
                                "ceo_email": profile.get('email', ''),
                                "ceo_linkedin": profile.get('linkedin_url', ''),
                                "confidence": "high",
                                "source": "RocketReach"
                            }
            
            return self._no_result("RocketReach API - no CEO found")
            
        except Exception as e:
            logger.error(f"RocketReach API error: {e}")
            return self._error_result("RocketReach API error", str(e))
        """Very aggressive online search for CEO info"""
        search_queries = [
            f"{company_name} CEO",
            f"{company_name} founder", 
            f"{company_name} president",
            f"{company_name} owner",
            f'"{company_name}" CEO',
            f"{company_name} leadership",
            f"{company_name} executive team"
        ]
        
        all_results = []
        
        for query in search_queries[:4]:  # Limit to avoid rate limiting
            try:
                logger.info(f"      Searching: {query}")
                self._rate_limit('search', 1.5)
                
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                response = self.session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    # Extract ALL text content from search results
                    snippets = re.findall(r'result__snippet[^>]*>(.*?)</a>', response.text, re.DOTALL)
                    titles = re.findall(r'result__title[^>]*>(.*?)</a>', response.text, re.DOTALL)
                    
                    for snippet in snippets[:2]:
                        clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                        clean_snippet = re.sub(r'\s+', ' ', clean_snippet).strip()
                        if len(clean_snippet) > 30:
                            all_results.append(clean_snippet)
                    
                    for title in titles[:2]:
                        clean_title = re.sub(r'<[^>]+>', '', title)
                        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                        if len(clean_title) > 10:
                            all_results.append(clean_title)
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.warning(f"      Search failed for {query}: {e}")
                continue
        
        if all_results:
            combined = " | ".join(all_results[:15])
            logger.info(f"      Found {len(all_results)} search results")
            return combined[:6000]
        else:
            logger.info(f"      No search results found")
            return ""
    
    def find_ceo_with_super_aggressive_openai(self, company_name: str, website_url: str = None, linkedin_url: str = None) -> Dict[str, Any]:
        """Super aggressive OpenAI CEO finding - will find ANYTHING that looks like a name"""
        try:
            self._rate_limit('openai', 1.0)
            
            # Get ALL available content
            context_parts = [f"Company: {company_name}"]
            
            # Add search results
            search_content = self.search_online_aggressively(company_name)
            if search_content:
                context_parts.append(f"Search results: {search_content}")
            
            # Add website content  
            if website_url:
                website_content = self.get_aggressive_website_content(website_url, company_name)
                if website_content:
                    context_parts.append(f"Website: {website_content}")
            
            if linkedin_url:
                context_parts.append(f"LinkedIn: {linkedin_url}")
            
            context = "\n\n".join(context_parts)
            
            # SUPER AGGRESSIVE PROMPT - will extract ANY name
            prompt = f"""You are a name extraction expert. Your job is to find ANY person's name associated with {company_name}.

AVAILABLE INFORMATION:
{context}

TASK: Find ANY person who might be associated with {company_name} leadership.

INSTRUCTIONS:
- Look for ANYONE mentioned as: CEO, founder, president, owner, director, manager, chairman, co-founder, executive, leader
- Even if not explicitly called "CEO", extract any person's name mentioned in a leadership context
- Look for names in phrases like "founded by", "started by", "led by", "created by", "owned by", "managed by"
- Extract names from sentences about company history, founding, leadership, management
- If you see ANY proper names (First Last) mentioned with the company, include them
- Be VERY generous - include any name that might be a leader
- Even if confidence is low, still extract the name

REQUIRED OUTPUT (JSON only):
{{
    "ceo_name": "Any person's name found (First Last format)",
    "ceo_title": "Their role/title if mentioned", 
    "confidence": "high/medium/low",
    "source": "Where you found the name",
    "additional_info": "Context about how you found this name"
}}

If you find MULTIPLE names, pick the most senior/leadership-oriented one.
If you find ANY name at all, return it even with low confidence.
Only return "Not found" if there are absolutely NO human names in the text.

Extract any leadership name you can find:"""

            if self.use_new_openai_api:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert at extracting human names from business content. You are very generous in finding names and never give up easily. Always return JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Slightly higher for more creative extraction
                    max_tokens=400
                )
                result_text = response.choices[0].message.content.strip()
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert at extracting human names from business content. You are very generous in finding names and never give up easily. Always return JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=400
                )
                result_text = response.choices[0].message.content.strip()
            
            return self._super_aggressive_parse(result_text, "Super Aggressive OpenAI", context)
            
        except Exception as e:
            logger.error(f"Super aggressive OpenAI failed: {e}")
            return self._error_result("OpenAI error", str(e))
    
    def find_ceo_with_aggressive_gemini(self, company_name: str, website_url: str = None, linkedin_url: str = None) -> Dict[str, Any]:
        """Aggressive Gemini CEO finding"""
        if not self.gemini_client:
            return self._no_result("Gemini not available")
        
        try:
            self._rate_limit('gemini', 1.0)
            
            # Build context
            context_parts = [f"Company: {company_name}"]
            
            # Add search content
            search_content = self.search_online_aggressively(company_name)
            if search_content:
                context_parts.append(f"Search results: {search_content}")
            
            if website_url:
                context_parts.append(f"Website: {website_url}")
            if linkedin_url:
                context_parts.append(f"LinkedIn: {linkedin_url}")
                
            context = "\n".join(context_parts)
            
            prompt = f"""Find ANY person associated with {company_name} leadership.

INFORMATION:
{context}

Look for ANY person's name mentioned as:
- CEO, founder, president, owner, director, manager, chairman, executive
- Anyone who "founded", "started", "created", "owns", "leads", "manages" the company
- Any person mentioned in connection with the company

Be very generous - if you see any human name, extract it.

Return JSON:
{{
"ceo_name": "Person's full name",
"ceo_title": "Their role",
"confidence": "high/medium/low", 
"source": "AI analysis",
"additional_info": "How you found this"
}}

Find any leadership name:"""

            response = self.gemini_client.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.4,
                    'max_output_tokens': 300,
                    'top_p': 0.95,
                    'top_k': 40
                }
            )
            
            result_text = response.text.strip()
            return self._super_aggressive_parse(result_text, "Aggressive Gemini", context)
            
        except Exception as e:
            logger.error(f"Aggressive Gemini failed: {e}")
            return self._error_result("Gemini error", str(e))
    
    def find_ceo_with_knowledge_mining(self, company_name: str) -> Dict[str, Any]:
        """Mine AI knowledge aggressively for any leadership info"""
        
        # Try multiple knowledge-based prompts
        prompts = [
            f"Who is the founder of {company_name}?",
            f"Who is the CEO of {company_name}?", 
            f"Who owns {company_name}?",
            f"Who started {company_name}?",
            f"Tell me about the leadership of {company_name}.",
            f"What do you know about {company_name} executives?"
        ]
        
        for prompt_text in prompts:
            try:
                self._rate_limit('openai_knowledge', 0.8)
                
                if self.use_new_openai_api:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "user", "content": f"{prompt_text} Give me any names you know, even if not 100% certain."}
                        ],
                        temperature=0.2,
                        max_tokens=200
                    )
                    result_text = response.choices[0].message.content.strip()
                else:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "user", "content": f"{prompt_text} Give me any names you know, even if not 100% certain."}
                        ],
                        temperature=0.2,
                        max_tokens=200
                    )
                    result_text = response.choices[0].message.content.strip()
                
                # Extract any name from the response
                name = self._extract_any_name_from_text(result_text)
                if name and name not in ['not', 'unknown', 'unclear', 'information', 'available']:
                    logger.info(f"    Knowledge mining found: {name}")
                    return {
                        "ceo_name": name,
                        "ceo_title": "Leadership",
                        "ceo_email": "",
                        "ceo_linkedin": "",
                        "confidence": "medium",
                        "source": f"AI Knowledge Mining - {prompt_text}"
                    }
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.warning(f"Knowledge mining prompt failed: {e}")
                continue
        
        return self._no_result("Knowledge mining found nothing")
    
    def _super_aggressive_parse(self, result_text: str, source: str, original_context: str = "") -> Dict[str, Any]:
        """Super aggressive parsing - will extract ANY name it can find"""
        logger.info(f"    Parsing {source}: {result_text[:150]}...")
        
        # Try JSON parsing first
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result_text = result_text.replace("**", "").replace("*", "").strip()
            
            if result_text.startswith('{'):
                try:
                    result = json.loads(result_text)
                    ceo_name = result.get('ceo_name', '')
                    if ceo_name and ceo_name not in ['Not found', 'Error', '', 'Unknown']:
                        result['source'] = source
                        logger.info(f"    ✓ JSON parsed name: {ceo_name}")
                        return result
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object
            json_match = re.search(r'\{[^}]*"ceo_name"[^}]*\}', result_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    ceo_name = result.get('ceo_name', '')
                    if ceo_name and ceo_name not in ['Not found', 'Error', '', 'Unknown']:
                        result['source'] = source
                        logger.info(f"    ✓ JSON extracted name: {ceo_name}")
                        return result
                except json.JSONDecodeError:
                    pass
            
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
        
        # SUPER AGGRESSIVE: Extract ANY name from the response text
        name = self._extract_any_name_from_text(result_text)
        if name:
            logger.info(f"    ✓ Aggressively extracted name: {name}")
            return {
                "ceo_name": name,
                "ceo_title": "Leadership",
                "ceo_email": "",
                "ceo_linkedin": "",
                "confidence": "low",
                "source": f"{source} - aggressive extraction"
            }
        
        # LAST RESORT: Extract from original context
        if original_context:
            context_name = self._extract_any_name_from_text(original_context)
            if context_name:
                logger.info(f"    ✓ Found name in context: {context_name}")
                return {
                    "ceo_name": context_name,
                    "ceo_title": "Found in content",
                    "ceo_email": "",
                    "ceo_linkedin": "",
                    "confidence": "low",
                    "source": f"{source} - context extraction"
                }
        
        logger.warning(f"    ✗ Could not extract any name from {source}")
        return self._no_result(f"{source} - no names found")
    
    def _extract_any_name_from_text(self, text: str) -> str:
        """Extract ANY human name from text - very aggressive"""
        if not text:
            return None
        
        # Multiple name extraction patterns
        patterns = [
            # Standard patterns
            r'(?:CEO|Chief Executive|President|Founder|Owner|Director|Manager|Chairman)[:\s]*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)',
            r'"ceo_name"[:\s]*"([^"]+)"',
            r'(?:founded|started|created|established|owned|led|managed)\s+by[:\s]*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)',
            
            # More aggressive patterns
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)(?:\s+(?:is|was|serves as|acts as))?\s+(?:CEO|Chief Executive|President|Founder|Owner)',
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+),?\s+(?:CEO|Chief Executive|President|Founder|Owner)',
            r'(?:Mr\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)',
            
            # Very broad patterns for any capitalized names
            r'\b([A-Z][a-zA-Z]{2,}\s+[A-Z][a-zA-Z]{2,})\b',
            
            # Names in quotes or specific formats
            r'"([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)"',
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\s+said',
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\s+explained',
        ]
        
        # Try each pattern
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                
                name = match.strip()
                
                # Filter out obvious non-names
                if (len(name) > 5 and 
                    len(name) < 50 and
                    not any(bad_word in name.lower() for bad_word in [
                        'not found', 'unknown', 'error', 'company', 'corporation', 
                        'limited', 'llc', 'inc', 'group', 'team', 'staff',
                        'information', 'available', 'website', 'linkedin'
                    ]) and
                    ' ' in name and  # Must have space (First Last)
                    name.count(' ') <= 3):  # Not too many words
                    
                    logger.info(f"      Extracted name: {name}")
                    return name
        
        return None
    
    def search_ceo_linkedin(self, ceo_name: str, company_name: str) -> str:
        """Search for LinkedIn profile using multiple methods with robust error handling"""
        if not ceo_name or ceo_name in ['Not found', 'Error', '']:
            return ""
        
        logger.info(f"        Searching for LinkedIn profile of: {ceo_name}")
        
        # Method 1: Try Google Custom Search first (if available)
        if self.google_search_client and self.google_search_engine_id:
            try:
                logger.info(f"        Trying Google Custom Search for LinkedIn...")
                self._rate_limit('google_linkedin_search', 1.0)
                
                query = f'"{ceo_name}" "{company_name}" site:linkedin.com/in'
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_search_client,
                    'cx': self.google_search_engine_id,
                    'q': query,
                    'num': 3
                }
                
                response = self.session.get(url, params=params, timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data:
                        for item in data['items']:
                            link = item.get('link', '')
                            if 'linkedin.com/in/' in link and len(link) > 30:
                                logger.info(f"        ✓ Google found LinkedIn: {link}")
                                return link
                
            except Exception as e:
                logger.warning(f"        Google Custom Search LinkedIn failed: {e}")
        
        # Method 2: Try DuckDuckGo with shorter timeout and better error handling
        search_queries = [
            f'"{ceo_name}" LinkedIn',
            f'{ceo_name} {company_name} LinkedIn'
        ]
        
        for query in search_queries[:1]:  # Limit to one query to avoid timeouts
            try:
                logger.info(f"        Trying DuckDuckGo search: {query}")
                self._rate_limit('linkedin_search', 2.0)
                
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                
                # Shorter timeout and better error handling
                response = self.session.get(search_url, timeout=6)
                if response.status_code == 200:
                    # Look for LinkedIn profile URLs
                    linkedin_patterns = [
                        r'https://[a-zA-Z0-9.-]*linkedin\.com/in/[a-zA-Z0-9-]+/?',
                        r'linkedin\.com/in/[a-zA-Z0-9-]+/?'
                    ]
                    
                    for pattern in linkedin_patterns:
                        matches = re.findall(pattern, response.text)
                        for match in matches[:2]:  # Only check first 2 matches
                            if not match.startswith('http'):
                                match = 'https://' + match
                            
                            if len(match) > 30 and '/in/' in match:
                                logger.info(f"        ✓ DuckDuckGo found LinkedIn: {match}")
                                return match
                
                # Small delay between attempts
                time.sleep(0.3)
                
            except requests.exceptions.Timeout:
                logger.warning(f"        DuckDuckGo search timed out for: {query}")
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"        DuckDuckGo connection failed for: {query}")
                continue
            except Exception as e:
                logger.warning(f"        DuckDuckGo search failed for {query}: {str(e)}")
                continue
        
        # Method 3: AI-based LinkedIn URL generation (fallback)
        try:
            logger.info(f"        Trying AI-based LinkedIn URL generation...")
            linkedin_url = self._generate_linkedin_url_with_ai(ceo_name, company_name)
            if linkedin_url:
                logger.info(f"        ✓ AI generated LinkedIn URL: {linkedin_url}")
                return linkedin_url
        except Exception as e:
            logger.warning(f"        AI LinkedIn generation failed: {e}")
        
        logger.info(f"        ✗ No LinkedIn profile found for {ceo_name}")
        return ""
    
    def _generate_linkedin_url_with_ai(self, ceo_name: str, company_name: str) -> str:
        """Use AI to generate most likely LinkedIn URL format"""
        try:
            self._rate_limit('ai_linkedin_gen', 1.0)
            
            prompt = f"""Based on the name "{ceo_name}" who works at "{company_name}", generate the most likely LinkedIn profile URL.

LinkedIn URLs follow the pattern: https://linkedin.com/in/[username]

Common username patterns:
- firstname-lastname
- firstnamelastname  
- firstname-lastname-numbers
- firstinitiallastname

For "{ceo_name}", what would be the most likely LinkedIn username?
Return ONLY the most probable LinkedIn URL, nothing else.

Example format: https://linkedin.com/in/john-smith"""

            if self.use_new_openai_api:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=50
                )
                result = response.choices[0].message.content.strip()
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=50
                )
                result = response.choices[0].message.content.strip()
            
            # Extract LinkedIn URL from response
            linkedin_match = re.search(r'https://linkedin\.com/in/[a-zA-Z0-9-]+/?', result)
            if linkedin_match:
                return linkedin_match.group()
            
        except Exception as e:
            logger.warning(f"AI LinkedIn generation error: {e}")
        
        return ""
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """Check if result has a valid name"""
        ceo_name = result.get('ceo_name', '')
        return (ceo_name and 
                ceo_name not in ['Not found', 'Error', '', 'Unknown', 'N/A'] and
                len(ceo_name.strip()) > 3 and
                not ceo_name.lower().startswith(('unknown', 'not found', 'error')))
    
    def _no_result(self, source: str) -> Dict[str, Any]:
        """No result response"""
        return {
            "ceo_name": "Not found",
            "ceo_title": "",
            "ceo_email": "",
            "ceo_linkedin": "",
            "confidence": "",
            "source": source
        }
    
    def _error_result(self, source: str, error_msg: str) -> Dict[str, Any]:
        """Error response"""
        return {
            "ceo_name": "Error", 
            "ceo_title": "Error",
            "ceo_email": "",
            "ceo_linkedin": "",
            "confidence": "none",
            "source": source
        }
    
    def find_ceo_ultra_aggressive(self, company_name: str, website_url: str = None, linkedin_url: str = None) -> Dict[str, Any]:
        """Ultra aggressive CEO finding - tries ALL available APIs and methods"""
        print(f"🔍 Searching for CEO of: {company_name}")
        
        # Method 1: Contact Database APIs (highest accuracy when available)
        if any(self.contact_apis.values()):
            print(f"  📇 Trying contact databases...")
            
            # Try Hunter.io
            if self.contact_apis.get('hunter') and website_url:
                result = self.try_hunter_api(company_name, website_url)
                if self._is_valid_result(result):
                    print(f"  ✅ Hunter.io found: {result['ceo_name']}")
                    return result
            
            # Try Apollo.io
            if self.contact_apis.get('apollo'):
                result = self.try_apollo_api(company_name, website_url)
                if self._is_valid_result(result):
                    print(f"  ✅ Apollo.io found: {result['ceo_name']}")
                    return result
            
            # Try RocketReach
            if self.contact_apis.get('rocketreach'):
                result = self.try_rocketreach_api(company_name, website_url)
                if self._is_valid_result(result):
                    print(f"  ✅ RocketReach found: {result['ceo_name']}")
                    return result
        
        # Method 2: Anthropic Claude
        if self.anthropic_client:
            print(f"  🤖 Trying Anthropic Claude...")
            result = self.find_ceo_with_anthropic(company_name, website_url, linkedin_url)
            if self._is_valid_result(result):
                print(f"  ✅ Claude found: {result['ceo_name']}")
                return result
        
        # Method 3: OpenAI
        print(f"  🧠 Trying OpenAI...")
        result = self.find_ceo_with_super_aggressive_openai(company_name, website_url, linkedin_url)
        if self._is_valid_result(result):
            print(f"  ✅ OpenAI found: {result['ceo_name']}")
            return result
        
        # Method 4: Gemini
        if self.gemini_client:
            print(f"  🔮 Trying Gemini...")
            result = self.find_ceo_with_aggressive_gemini(company_name, website_url, linkedin_url)
            if self._is_valid_result(result):
                print(f"  ✅ Gemini found: {result['ceo_name']}")
                return result
        
        # Method 5: Knowledge mining
        print(f"  📚 Trying knowledge base...")
        result = self.find_ceo_with_knowledge_mining(company_name)
        if self._is_valid_result(result):
            print(f"  ✅ Knowledge base found: {result['ceo_name']}")
            return result
        
        # Return best attempt
        print(f"  ❌ No CEO found for {company_name}")
        return self._no_result("All methods failed")
    
    def try_hunter_api(self, company_name: str, website_url: str) -> Dict[str, Any]:
        """Try Hunter.io API"""
        if not self.contact_apis.get('hunter'):
            return self._no_result("Hunter API not available")
        
        try:
            domain = website_url.replace('https://', '').replace('http://', '').split('/')[0]
            self._rate_limit('hunter', 2.0)
            
            url = f"https://api.hunter.io/v2/domain-search"
            params = {
                'domain': domain,
                'api_key': self.contact_apis['hunter'],
                'limit': 50
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'emails' in data['data']:
                    for email_info in data['data']['emails']:
                        position = email_info.get('position', '').lower()
                        if any(title in position for title in ['ceo', 'chief executive', 'president', 'founder', 'owner']):
                            return {
                                "ceo_name": f"{email_info.get('first_name', '')} {email_info.get('last_name', '')}".strip(),
                                "ceo_title": email_info.get('position', 'CEO'),
                                "ceo_email": email_info.get('value', ''),
                                "ceo_linkedin": "",
                                "confidence": "high",
                                "source": "Hunter.io"
                            }
            
            return self._no_result("Hunter API - no CEO found")
            
        except Exception as e:
            logger.error(f"Hunter API error: {e}")
            return self._error_result("Hunter API error", str(e))
    
    def load_existing_results(self, output_file_path: str) -> pd.DataFrame:
        """Load existing results"""
        try:
            if os.path.exists(output_file_path):
                logger.info(f"Loading existing results: {output_file_path}")
                return pd.read_csv(output_file_path)
            return None
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return None
    
    def save_progress(self, df: pd.DataFrame, output_file_path: str, current_index: int):
        """Save progress"""
        try:
            df.to_csv(output_file_path, index=False)
            logger.info(f"Progress saved after {current_index + 1} companies")
        except Exception as e:
            logger.error(f"Save error: {e}")
    
    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Detect column names"""
        columns = {}
        
        for col in df.columns:
            col_lower = col.lower().strip()
            
            if not columns.get('company'):
                if any(term in col_lower for term in ['company', 'business', 'organization', 'firm', 'name']):
                    columns['company'] = col
            
            if not columns.get('website'):
                if any(term in col_lower for term in ['website', 'web', 'url', 'domain', 'site']):
                    columns['website'] = col
            
            if not columns.get('linkedin'):
                if 'linkedin' in col_lower:
                    columns['linkedin'] = col
        
        return columns
    
    def process_csv(self, csv_file_path: str, output_file_path: str = None) -> pd.DataFrame:
        """Process CSV with targeted reprocessing for missing CEOs"""
        
        # Read CSV
        df = pd.read_csv(csv_file_path)
        logger.info(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
        
        # Set output path
        if output_file_path is None:
            base_name = csv_file_path.replace('.csv', '')
            output_file_path = f"{base_name}_with_ceos.csv"
        
        # Check for existing results
        existing_df = self.load_existing_results(output_file_path)
        processing_mode = 'new'
        empty_ceo_indices = []
        start_index = 0
        
        if existing_df is not None:
            # Analyze existing results
            total_existing = len(existing_df)
            has_valid_ceo = (existing_df['ceo_name'].notna() & 
                           (existing_df['ceo_name'] != '') & 
                           (existing_df['ceo_name'] != 'Not found') & 
                           (existing_df['ceo_name'] != 'Error'))
            processed_count = has_valid_ceo.sum()
            
            # Find missing CEO rows
            empty_ceo_mask = ~has_valid_ceo
            empty_ceo_indices = existing_df[empty_ceo_mask].index.tolist()
            empty_count = len(empty_ceo_indices)
            
            logger.info(f"Existing results:")
            logger.info(f"  Total: {total_existing}")
            logger.info(f"  Found CEOs: {processed_count}")
            logger.info(f"  Missing CEOs: {empty_count}")
            
            if empty_count == 0:
                logger.info("All companies already have CEO data!")
                return existing_df
            
            print(f"\nExisting results found:")
            print(f"  ✓ {processed_count} companies have CEO data")
            print(f"  ✗ {empty_count} companies missing CEO data")
            
            choice = input(f"\nChoose mode:\n1. Process ONLY missing CEOs ({empty_count} companies) ⭐ RECOMMENDED\n2. Continue sequential processing\n3. Start completely over\n4. Cancel\nChoice (1-4): ").strip()
            
            if choice == '1':
                df = existing_df.copy()
                processing_mode = 'empty_only'
                logger.info(f"TARGETED MODE: Will process only {empty_count} missing companies")
                
            elif choice == '2':
                df = existing_df.copy()
                processing_mode = 'continue'
                for idx, row in df.iterrows():
                    if pd.isna(row.get('ceo_name')) or row.get('ceo_name') in ['', 'Not found', 'Error']:
                        start_index = idx
                        break
                else:
                    logger.info("All processed!")
                    return df
                logger.info(f"Continuing from row {start_index + 1}")
                
            elif choice == '3':
                processing_mode = 'new'
                logger.info("Starting fresh...")
                
            elif choice == '4':
                logger.info("Cancelled")
                return None
            else:
                logger.warning("Invalid choice, starting fresh")
                processing_mode = 'new'
        
        # Detect columns
        columns = self._detect_columns(df)
        logger.info(f"Detected columns: {columns}")
        
        if not columns.get('company'):
            raise ValueError("Could not find company name column!")
        
        company_col = columns['company']
        website_col = columns.get('website')
        linkedin_col = columns.get('linkedin')
        
        # Initialize result columns with proper string dtype
        result_columns = ['ceo_name', 'ceo_title', 'ceo_email', 'ceo_linkedin', 'confidence', 'source']
        for col in result_columns:
            if col not in df.columns:
                df[col] = pd.Series(dtype='string')  # Use pandas string dtype
            else:
                # Convert existing columns to string dtype to avoid dtype warnings
                df[col] = df[col].astype('string')
        
        # Ensure all result columns can handle string values properly
        for col in result_columns:
            df[col] = df[col].fillna('').astype('string')
        
        # PROCESSING MODES
        if processing_mode == 'empty_only':
            # TARGETED PROCESSING - Only missing CEOs
            companies_to_process = len(empty_ceo_indices)
            logger.info(f"\n🎯 TARGETED PROCESSING MODE")
            logger.info(f"Processing {companies_to_process} companies with missing CEO data")
            
            if companies_to_process > 0:
                print(f"\nSample companies to process:")
                for i, idx in enumerate(empty_ceo_indices[:5]):
                    company_name = df.iloc[idx][company_col]
                    current_status = df.iloc[idx].get('ceo_name', 'Empty')
                    print(f"  {i+1}. {company_name} (status: {current_status})")
                if len(empty_ceo_indices) > 5:
                    print(f"  ... and {len(empty_ceo_indices) - 5} more")
            
            # Process each missing CEO company
            for i, index in enumerate(empty_ceo_indices):
                try:
                    row = df.iloc[index]
                    company_name = row[company_col]
                    
                    if pd.isna(company_name) or str(company_name).strip() == '':
                        logger.warning(f"Skipping invalid company at row {index + 1}")
                        continue
                    
                    company_name = str(company_name).strip()
                    website_url = self._clean_url(row, website_col)
                    linkedin_url = self._clean_url(row, linkedin_col)
                    
                    logger.info(f"Processing {i + 1}/{companies_to_process}: {company_name} (row {index + 1})")
                    
                    # ULTRA AGGRESSIVE CEO FINDING
                    ceo_info = self.find_ceo_ultra_aggressive(company_name, website_url, linkedin_url)
                    
                    # Update DataFrame with proper string assignment
                    df.at[index, 'ceo_name'] = str(ceo_info.get('ceo_name', '')) if ceo_info.get('ceo_name') else ''
                    df.at[index, 'ceo_title'] = str(ceo_info.get('ceo_title', '')) if ceo_info.get('ceo_title') else ''
                    df.at[index, 'ceo_email'] = str(ceo_info.get('ceo_email', '')) if ceo_info.get('ceo_email') else ''
                    df.at[index, 'confidence'] = str(ceo_info.get('confidence', '')) if ceo_info.get('confidence') else ''
                    df.at[index, 'source'] = str(ceo_info.get('source', '')) if ceo_info.get('source') else ''
                    
                    # Search LinkedIn if CEO found
                    ceo_linkedin = ""
                    if (self._is_valid_result(ceo_info) and not ceo_info.get('ceo_linkedin')):
                        logger.info(f"      Searching LinkedIn...")
                        ceo_linkedin = self.search_ceo_linkedin(ceo_info['ceo_name'], company_name)
                    elif ceo_info.get('ceo_linkedin'):
                        ceo_linkedin = str(ceo_info['ceo_linkedin'])
                    
                    # Properly assign LinkedIn URL as string
                    df.at[index, 'ceo_linkedin'] = str(ceo_linkedin) if ceo_linkedin else ''
                    
                    # Save progress every 3 companies
                    if (i + 1) % 3 == 0:
                        self.save_progress(df, output_file_path, index)
                        logger.info(f"✓ Processed {i + 1}/{companies_to_process} missing CEOs")
                    
                    time.sleep(1)  # Rate limiting
                    
                except KeyboardInterrupt:
                    logger.info(f"Interrupted at company #{i + 1}")
                    self.save_progress(df, output_file_path, index)
                    logger.info("Progress saved!")
                    return df
                    
                except Exception as e:
                    logger.error(f"Error processing {company_name}: {e}")
                    continue
            
            # Final save for targeted mode
            self.save_progress(df, output_file_path, empty_ceo_indices[-1] if empty_ceo_indices else 0)
            logger.info(f"✅ Completed targeted processing of {companies_to_process} companies")
            
        elif processing_mode == 'continue':
            # SEQUENTIAL PROCESSING
            total_companies = len(df)
            logger.info(f"\n➡️ SEQUENTIAL MODE: Starting from row {start_index + 1}")
            
            for index in range(start_index, total_companies):
                self._process_single_company(df, index, company_col, website_col, linkedin_col, output_file_path, index + 1, total_companies)
            
        else:
            # FULL PROCESSING
            total_companies = len(df)
            logger.info(f"\n🔄 FULL PROCESSING MODE: {total_companies} companies")
            
            for index in range(total_companies):
                self._process_single_company(df, index, company_col, website_col, linkedin_col, output_file_path, index + 1, total_companies)
        
        # Final save
        self.save_progress(df, output_file_path, len(df) - 1)
        logger.info(f"\n🎉 PROCESSING COMPLETE!")
        logger.info(f"Results saved to: {output_file_path}")
        
        return df
    
    def _clean_url(self, row, col_name):
        """Clean URL from row"""
        if not col_name or pd.isna(row.get(col_name)):
            return None
        
        url = str(row[col_name]).strip()
        if url and url not in ['nan', 'None', '']:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        return None
    
    def _process_single_company(self, df: pd.DataFrame, index: int, company_col: str, website_col: str, linkedin_col: str, output_file_path: str, current_num: int, total_num: int):
        """Process a single company"""
        try:
            row = df.iloc[index]
            company_name = row[company_col]
            
            if pd.isna(company_name) or str(company_name).strip() == '':
                logger.warning(f"Skipping invalid company at row {index + 1}")
                return
            
            company_name = str(company_name).strip()
            website_url = self._clean_url(row, website_col)
            linkedin_url = self._clean_url(row, linkedin_col)
            
            logger.info(f"Processing {current_num}/{total_num}: {company_name}")
            
            # ULTRA AGGRESSIVE CEO FINDING
            ceo_info = self.find_ceo_ultra_aggressive(company_name, website_url, linkedin_url)
            
            # Update DataFrame with proper string types
            df.at[index, 'ceo_name'] = str(ceo_info.get('ceo_name', '')) if ceo_info.get('ceo_name') else ''
            df.at[index, 'ceo_title'] = str(ceo_info.get('ceo_title', '')) if ceo_info.get('ceo_title') else ''
            df.at[index, 'ceo_email'] = str(ceo_info.get('ceo_email', '')) if ceo_info.get('ceo_email') else ''
            df.at[index, 'confidence'] = str(ceo_info.get('confidence', '')) if ceo_info.get('confidence') else ''
            df.at[index, 'source'] = str(ceo_info.get('source', '')) if ceo_info.get('source') else ''
            
            # Search LinkedIn if CEO found
            ceo_linkedin = ""
            if (self._is_valid_result(ceo_info) and not ceo_info.get('ceo_linkedin')):
                logger.info(f"      Searching LinkedIn...")
                ceo_linkedin = self.search_ceo_linkedin(ceo_info['ceo_name'], company_name)
            elif ceo_info.get('ceo_linkedin'):
                ceo_linkedin = str(ceo_info['ceo_linkedin'])
            
            # Properly assign LinkedIn URL as string
            df.at[index, 'ceo_linkedin'] = str(ceo_linkedin) if ceo_linkedin else ''
            
            # Save every 3 companies
            if current_num % 3 == 0:
                self.save_progress(df, output_file_path, index)
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info(f"Interrupted at company #{current_num}")
            self.save_progress(df, output_file_path, index)
            raise
            
        except Exception as e:
            logger.error(f"Error processing {company_name}: {e}")

def load_api_keys_from_env() -> Dict[str, str]:
    """Load API keys"""
    api_keys = {}
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        api_keys['openai'] = openai_key
        print("✓ OpenAI API key loaded")
    else:
        print("❌ OPENAI_API_KEY required in .env file")
        return None
    
    # Optional APIs with Google Custom Search
    optional_apis = {
        'GEMINI_API_KEY': 'gemini',
        'ANTHROPIC_API_KEY': 'anthropic',
        'GOOGLE_SEARCH_API_KEY': 'google_search',
        'GOOGLE_SEARCH_CX': 'google_search_cx',
        'HUNTER_API_KEY': 'hunter',
        'APOLLO_API_KEY': 'apollo',
        'CLEARBIT_API_KEY': 'clearbit',
        'ROCKETREACH_API_KEY': 'rocketreach'
    }
    
    for env_var, key_name in optional_apis.items():
        api_key = os.getenv(env_var)
        if api_key:
            api_keys[key_name] = api_key
            print(f"✓ {key_name.title()} API key loaded")
    
    print(f"✓ Loaded {len(api_keys)} API keys")
    return api_keys

def check_dependencies():
    """Check required packages"""
    required = {'pandas': 'pandas', 'requests': 'requests', 'openai': 'openai', 'python-dotenv': 'dotenv'}
    
    missing = []
    for package, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.error(f"Missing packages: {missing}")
        print("Install missing packages:")
        for package in missing:
            print(f"  pip install {package}")
        return False
    
    return True

def find_csv_files():
    """Find CSV files"""
    import glob
    return glob.glob("*.csv")

def display_results_summary(df: pd.DataFrame):
    """Display results summary"""
    total = len(df)
    
    has_valid_ceo = (df['ceo_name'].notna() & 
                    (df['ceo_name'] != 'Not found') & 
                    (df['ceo_name'] != '') & 
                    (df['ceo_name'] != 'Error'))
    found = has_valid_ceo.sum()
    missing = total - found
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total companies: {total}")
    print(f"✅ CEOs found: {found} ({found/total*100:.1f}%)")
    print(f"❌ Missing CEO data: {missing} ({missing/total*100:.1f}%)")
    
    # Confidence breakdown
    if 'confidence' in df.columns and found > 0:
        confidence_counts = df[has_valid_ceo]['confidence'].value_counts()
        print(f"\nConfidence levels:")
        for conf, count in confidence_counts.items():
            if conf and conf != '':
                percentage = count/found*100
                print(f"  {conf.title()}: {count} ({percentage:.1f}%)")
    
    # Source breakdown
    if 'source' in df.columns and found > 0:
        print(f"\nSources used:")
        source_counts = df[has_valid_ceo]['source'].value_counts()
        for source, count in source_counts.head(5).items():
            if source and source != '':
                percentage = count/found*100
                print(f"  {source}: {count} ({percentage:.1f}%)")
    
    # Sample results
    successful = df[has_valid_ceo]
    if len(successful) > 0:
        print(f"\n✅ Sample successful results:")
        display_cols = [col for col in [df.columns[0], 'ceo_name', 'ceo_title', 'confidence'] if col in df.columns]
        print(successful[display_cols].head(3).to_string(index=False))
    
    # Sample missing
    if missing > 0:
        print(f"\n❌ Sample companies still missing CEO data:")
        missing_df = df[~has_valid_ceo]
        company_col = df.columns[0]
        for idx, row in missing_df.head(3).iterrows():
            company_name = row[company_col]
            status = row.get('ceo_name', 'Empty')
            print(f"  • {company_name} (Status: {status})")
        
        print(f"\n💡 To retry missing CEOs: Run tool again and select option 1")

def add_analysis_command():
    """Analysis command"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        csv_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        if not csv_file:
            csv_files = find_csv_files()
            if not csv_files:
                print("No CSV files found")
                return True
            csv_file = csv_files[0]
        
        try:
            df = pd.read_csv(csv_file)
            print(f"Analyzing: {csv_file}")
            display_results_summary(df)
        except Exception as e:
            print(f"Analysis error: {e}")
        
        return True
    return False

def main():
    """Main function"""
    print("="*60)
    print("🚀 ULTRA AGGRESSIVE CEO FINDER")
    print("="*60)
    print("Optimized for MAXIMUM success rate!")
    
    # Analysis mode
    if add_analysis_command():
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Load API keys
    logger.info("Loading API keys...")
    api_keys = load_api_keys_from_env()
    
    if not api_keys:
        print("\n❌ Missing API keys")
        print("Create a .env file with at least OPENAI_API_KEY")
        return
    
    # Find CSVs
    csv_files = find_csv_files()
    if not csv_files:
        print("❌ No CSV files found")
        print("Place your CSV file in this directory")
        return
    
    # Select CSV
    print(f"\nFound {len(csv_files)} CSV file(s):")
    for i, file in enumerate(csv_files, 1):
        try:
            temp_df = pd.read_csv(file)
            if 'ceo_name' in temp_df.columns:
                has_valid_ceo = (temp_df['ceo_name'].notna() & 
                               (temp_df['ceo_name'] != 'Not found') & 
                               (temp_df['ceo_name'] != '') & 
                               (temp_df['ceo_name'] != 'Error'))
                found_count = has_valid_ceo.sum()
                total_count = len(temp_df)
                missing_count = total_count - found_count
                print(f"  {i}. {file} [✅ {found_count}/{total_count} CEOs, ❌ {missing_count} missing]")
            else:
                print(f"  {i}. {file} [📊 {len(temp_df)} companies, no CEO data yet]")
        except:
            print(f"  {i}. {file}")
    
    if len(csv_files) == 1:
        input_csv = csv_files[0]
        print(f"\nUsing: {input_csv}")
    else:
        while True:
            try:
                choice = int(input(f"\nSelect CSV (1-{len(csv_files)}): ")) - 1
                if 0 <= choice < len(csv_files):
                    input_csv = csv_files[choice]
                    break
                else:
                    print("Invalid choice")
            except ValueError:
                print("Enter a number")
    
    # Preview
    try:
        preview_df = pd.read_csv(input_csv)
        print(f"\n📊 CSV Preview:")
        print(f"  Companies: {len(preview_df)}")
        print(f"  Columns: {list(preview_df.columns)}")
        
        if 'ceo_name' in preview_df.columns:
            has_valid_ceo = (preview_df['ceo_name'].notna() & 
                           (preview_df['ceo_name'] != 'Not found') & 
                           (preview_df['ceo_name'] != '') & 
                           (preview_df['ceo_name'] != 'Error'))
            found_count = has_valid_ceo.sum()
            missing_count = len(preview_df) - found_count
            
            print(f"  ✅ CEOs found: {found_count}")
            print(f"  ❌ Missing: {missing_count}")
            if missing_count > 0:
                print(f"  💡 Use 'Process ONLY missing CEOs' mode for efficiency")
        
        proceed = input(f"\nProceed? (y/n): ").lower().strip()
        if proceed != 'y':
            print("Cancelled")
            return
            
    except Exception as e:
        logger.error(f"CSV preview error: {e}")
        return
    
    # Process
    try:
        ceo_finder = CEOFinder(api_keys)
        output_csv = input_csv.replace('.csv', '_with_ceos.csv')
        
        print(f"\n🚀 Starting ULTRA AGGRESSIVE CEO finding...")
        print(f"📄 Output: {output_csv}")
        print(f"📝 Log: ceo_finder.log")
        
        results_df = ceo_finder.process_csv(input_csv, output_csv)
        
        if results_df is not None:
            display_results_summary(results_df)
            print(f"\n🎉 PROCESSING COMPLETE!")
            print(f"📄 Results: {output_csv}")
            print(f"📊 Analysis: python {__file__} --analyze {output_csv}")
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()