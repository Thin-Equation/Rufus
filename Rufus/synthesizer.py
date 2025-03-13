from openai import OpenAI
from logger import logger
import re
import json
import os
from datetime import datetime

def synthesize_document(scraped_data, instructions, nim_api_key, model="deepseek-ai/deepseek-r1", output_dir="outputs"):
    """
    Synthesize scraped data into a structured document using Nvidia's NIM API
    through the OpenAI client package (without using guided_json).
    """
    logger.info(f"Synthesizing document from {len(scraped_data)} pages using model: {model}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Combine the scraped text from all pages
    combined_text = "\n\n".join(
        [f"URL: {url}\nContent: {content}" for url, content in scraped_data.items()]
    )
    
    logger.debug(f"Combined text length: {len(combined_text)} characters")
    
    # Save the combined content to a text file
    content_filename = f"{output_dir}/web_content_{timestamp}.txt"
    with open(content_filename, "w", encoding="utf-8") as f:
        f.write(combined_text)
    
    logger.info(f"Web content saved to {content_filename}")
    
    try:
        logger.debug("Initializing OpenAI client with NIM configuration")
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nim_api_key
        )
        
        # Read the content from file
        with open(content_filename, "r", encoding="utf-8") as f:
            web_content = f.read()
            
        # Create a detailed prompt with explicit formatting instructions
        prompt = f"""
        You are tasked with creating a structured JSON document based on web content and user instructions.

        INSTRUCTIONS: {instructions}
        
        WEB CONTENT:
        {web_content}
        
        OUTPUT REQUIREMENTS:
        1. If the web content is empty, return only: {{"response": "NO WEB CONTENT (Not a registered domain)"}}
        2. For non-empty content, create a JSON document with these fields:
           - title: A descriptive title summarizing the content
           - summary: Brief summary of key information (2-3 sentences)
           - key_points: Array of main points/takeaways
           - content_sections: Array of objects with "heading" and "content" fields
           - metadata: Object with source count and processing timestamp
        
        3. If the instructions mention HR or chatbot, include:
           - For HR: Include "policies" array with HR-related information
           - For chatbots: Include "faq" array with question/answer pairs

        4. IMPORTANT: Return ONLY valid JSON without any explanation, markdown formatting, or code block markers.
        5. Ensure proper JSON syntax with quotes around property names.
        """
        
        logger.info("Making API call to NIM for document synthesis")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            top_p=0.7,
            response_format={"type": "json_object"}  # Request JSON format but without schema constraints
        )
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            logger.debug(f"Received response: {len(content)} characters")
        else:
            logger.error("No content in response from NIM API")
            return {"error": "No content in response"}
        
        # Clean the response to ensure it's valid JSON
        clean_content = clean_response(content)
        
        try:
            # Attempt to parse as JSON
            structured_document = json.loads(clean_content)
            logger.info("Successfully parsed response as JSON")
            
            # Save the JSON response to a file
            json_filename = f"{output_dir}/structured_document_{timestamp}.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(structured_document, f, indent=2)
                
            logger.info(f"Structured document saved to {json_filename}")
            
            return structured_document
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse response as JSON: {str(e)}")
            
            # Additional cleaning attempt for common JSON errors
            try:
                # Fix missing quotes around property names
                fixed_content = re.sub(r'(\s*?)(\w+)(\s*?):', r'\1"\2"\3:', clean_content)
                # Replace single quotes with double quotes
                fixed_content = fixed_content.replace("'", '"')
                
                structured_document = json.loads(fixed_content)
                logger.info("Successfully parsed response as JSON after fixing")
                
                # Save the fixed JSON
                json_filename = f"{output_dir}/structured_document_{timestamp}.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(structured_document, f, indent=2)
                    
                logger.info(f"Fixed structured document saved to {json_filename}")
                
                return structured_document
            except json.JSONDecodeError:
                # If still can't parse, create a fallback response
                logger.error("Failed to parse response even after fixes")
                
                # If the response contains "NO WEB CONTENT" but isn't valid JSON, format it properly
                result = {"content": clean_content, "parse_error": str(e)}
                if "NO WEB CONTENT" in clean_content:
                    result = {"response": "NO WEB CONTENT"}
                
                    # Save the result anyway
                    json_filename = f"{output_dir}/structured_document_{timestamp}.json"
                    with open(json_filename, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2)
                    
                logger.info(f"Fallback document saved to {json_filename}")
                
                return result
            
    except Exception as e:
        # In case of an API error, return the error message
        logger.error(f"Error in API call: {str(e)}", exc_info=True)
        return {"error": str(e)}

def clean_response(content):
    """Clean the LLM response by removing thinking blocks and markdown formatting."""
    # Remove any <think>...</think> blocks
    clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    
    # Remove markdown code block markers
    clean_content = re.sub(r'```json', '', clean_content)
    clean_content = re.sub(r'```', '', clean_content)
    
    # Strip whitespace
    clean_content = clean_content.strip()
    
    return clean_content
