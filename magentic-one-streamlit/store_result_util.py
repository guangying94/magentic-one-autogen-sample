"""
Azure Storage Utilities for Magentic-One Results

This module handles all Azure storage operations including:
- Azure Cosmos DB for storing run metadata and results
- Azure Blob Storage for storing images
- Azure Identity authentication for secure access
"""

import os
import json
import base64
import streamlit as st
from datetime import datetime
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

class AzureStorageManager:
    """Manages Azure Cosmos DB and Blob Storage operations for storing run results."""
    
    def __init__(self):
        self.storage_enabled = os.getenv('STORE_RUN_RESULT', '').lower() == 'true'
        self._blob_service_client = None
        self._cosmos_container = None
    
    def is_enabled(self) -> bool:
        """Check if Azure storage is enabled."""
        return self.storage_enabled
    
    def get_blob_service_client(self):
        """Initialize and return Azure Blob Storage client if enabled."""
        if not self.storage_enabled:
            return None
        
        if self._blob_service_client is not None:
            return self._blob_service_client
        
        storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        if not storage_account_url:
            st.error("Azure Storage Account URL must be set in AZURE_STORAGE_ACCOUNT_URL environment variable")
            return None
        
        try:
            # Use Azure Identity for authentication
            credential = DefaultAzureCredential()
            self._blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)
            return self._blob_service_client
        except Exception as e:
            st.error(f"Failed to connect to Azure Blob Storage: {e}")
            return None
    
    def get_cosmos_client(self):
        """Initialize and return Azure Cosmos DB client if enabled."""
        if not self.storage_enabled:
            return None
        
        if self._cosmos_container is not None:
            return self._cosmos_container
        
        endpoint = os.getenv('COSMOS_ENDPOINT')
        database_name = os.getenv('COSMOS_DATABASE', 'magentic_one_results')
        container_name = os.getenv('COSMOS_CONTAINER', 'run_results')
        
        if not endpoint:
            st.error("Cosmos DB endpoint must be set in COSMOS_ENDPOINT environment variable")
            return None
        
        try:
            # Use Azure Identity for authentication
            credential = DefaultAzureCredential()
            client = CosmosClient(endpoint, credential)
            database = client.get_database_client(database_name)
            self._cosmos_container = database.get_container_client(container_name)
            return self._cosmos_container
        except Exception as e:
            st.error(f"Failed to connect to Cosmos DB: {e}")
            return None
    
    def upload_image_to_blob(self, image_data: str, run_id: str, image_index: int) -> str:
        """Upload base64 image to Azure Blob Storage and return the URL."""
        if not self.storage_enabled:
            return None
        
        blob_service_client = self.get_blob_service_client()
        if not blob_service_client:
            return None
        
        container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'magentic-one-images')
        
        try:
            # Create container if it doesn't exist
            try:
                container_client = blob_service_client.get_container_client(container_name)
                container_client.get_container_properties()
            except:
                # Container doesn't exist, create it (private access since public is disabled)
                blob_service_client.create_container(container_name)
                container_client = blob_service_client.get_container_client(container_name)
            
            # Generate blob name
            blob_name = f"{run_id}/image_{image_index}.png"
            
            # Convert base64 to bytes
            image_bytes = base64.b64decode(image_data)
            
            # Upload the blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(image_bytes, overwrite=True, content_type='image/png')
            
            # Return the blob URL (even though it's not publicly accessible)
            return blob_client.url
            
        except Exception as e:
            st.error(f"Failed to upload image to blob storage: {e}")
            return None
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def download_image_from_blob(_self, blob_url: str) -> bytes:
        """Download image from Azure Blob Storage using authenticated client."""
        if not _self.storage_enabled:
            return None
        
        blob_service_client = _self.get_blob_service_client()
        if not blob_service_client:
            return None
        
        try:
            # Parse the blob URL to extract container and blob name
            # URL format: https://account.blob.core.windows.net/container/path/to/blob
            url_parts = blob_url.split('/')
            
            # We know the container name from our environment variable
            container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'magentic-one-images')
            
            # URL structure: https://account.blob.core.windows.net/container/run_id/image_x.png
            # url_parts[0] = 'https:'
            # url_parts[1] = ''
            # url_parts[2] = 'account.blob.core.windows.net'
            # url_parts[3] = 'container'
            # url_parts[4] = 'run_id'
            # url_parts[5] = 'image_x.png'
            
            if len(url_parts) >= 5:
                # The blob name starts from index 4 (everything after the container)
                blob_name = '/'.join(url_parts[4:])
            else:
                # Fallback: assume last part is the blob name
                blob_name = url_parts[-1]
            
            # Get the blob client and download the image
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            # Download the blob data
            blob_data = blob_client.download_blob()
            return blob_data.readall()
            
        except Exception as e:
            st.error(f"Failed to download image from blob storage: {e}")
            st.error(f"URL parts: {url_parts if 'url_parts' in locals() else 'N/A'}")
            st.error(f"Container: {container_name if 'container_name' in locals() else 'N/A'}")
            st.error(f"Blob: {blob_name if 'blob_name' in locals() else 'N/A'}")
            return None
    
    def store_run_result(self, run_id: str, prompt: str, results: list, model_name: str, 
                        use_aoai: bool, elapsed_time: float, prompt_tokens: int, completion_tokens: int):
        """Store run result in Azure Cosmos DB with images stored in Blob Storage."""
        if not self.storage_enabled:
            st.info("ℹ️ Storage is disabled. Set STORE_RUN_RESULT=true to enable.")
            return
        
        container = self.get_cosmos_client()
        if not container:
            st.error("❌ Failed to connect to Cosmos DB. Check your authentication and endpoint configuration.")
            return
        
        # Convert results to serializable format
        serialized_results = []
        total_size = 0
        max_document_size = 1.5 * 1024 * 1024  # 1.5 MB to leave room for metadata
        image_index = 0
        
        for chunk in results:
            if chunk is None:
                continue
            if hasattr(chunk, '__class__'):
                chunk_data = {
                    'type': chunk.__class__.__name__,
                    'source': getattr(chunk, 'source', None),
                    'content': None,
                    'timestamp': datetime.now().isoformat()
                }
                
                if chunk.__class__.__name__ == 'TaskResult':
                    # Store task completion info
                    chunk_data['content'] = f"Task completed in {elapsed_time:.2f} seconds"
                elif hasattr(chunk, 'type') and chunk.type == 'MultiModalMessage':
                    # Handle images - upload to blob storage instead of storing inline
                    if len(chunk.content) > 1:
                        image_data = chunk.content[1].to_base64()
                        
                        # Upload image to blob storage
                        blob_url = self.upload_image_to_blob(image_data, run_id, image_index)
                        image_index += 1
                        
                        if blob_url:
                            chunk_data['content'] = {
                                'type': 'image',
                                'blob_url': blob_url,
                                'size_kb': round(len(image_data) * 3 / 4 / 1024, 1)  # Approximate original size
                            }
                        else:
                            chunk_data['content'] = {
                                'type': 'image',
                                'blob_url': None,
                                'note': "Failed to upload image to blob storage"
                            }
                    else:
                        chunk_data['content'] = {
                            'type': 'image',
                            'blob_url': None,
                            'note': "No image content available"
                        }
                elif hasattr(chunk, 'content'):
                    # Store text content, but truncate if too long
                    content_str = str(chunk.content)
                    if len(content_str) > 100000:  # Truncate very long text content
                        content_str = content_str[:100000] + "... [Content truncated due to size limits]"
                    chunk_data['content'] = content_str
                
                # Estimate the size of this chunk when serialized (should be much smaller now without images)
                chunk_json = json.dumps(chunk_data)
                chunk_size = len(chunk_json.encode('utf-8'))
                
                # Check if adding this chunk would exceed the size limit
                if total_size + chunk_size > max_document_size:
                    # Add a note that some content was truncated
                    truncation_note = {
                        'type': 'TruncationNote',
                        'source': 'system',
                        'content': f"Results truncated at {len(serialized_results)} items due to Cosmos DB 2MB size limit",
                        'timestamp': datetime.now().isoformat()
                    }
                    serialized_results.append(truncation_note)
                    break
                
                serialized_results.append(chunk_data)
                total_size += chunk_size
        
        document = {
            'id': run_id,
            'prompt': prompt,
            'model_name': model_name,
            'use_azure_openai': use_aoai,
            'elapsed_time': elapsed_time,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'results': serialized_results,
            'created_at': datetime.now().isoformat(),
            'document_size_mb': round(total_size / (1024 * 1024), 2),
            'total_images': image_index
        }
        
        try:
            container.create_item(document)
            if image_index > 0:
                st.success(f"Run result stored with ID: {run_id} (Size: {document['document_size_mb']:.2f} MB, {image_index} images in blob storage)")
            else:
                st.success(f"Run result stored with ID: {run_id} (Size: {document['document_size_mb']:.2f} MB)")
        except Exception as e:
            # If still too large, try storing just the metadata
            if "request size is too large" in str(e).lower() or "413" in str(e):
                st.warning(f"Result too large for Cosmos DB. Storing metadata only.")
                minimal_document = {
                    'id': run_id,
                    'prompt': prompt,
                    'model_name': model_name,
                    'use_azure_openai': use_aoai,
                    'elapsed_time': elapsed_time,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'results': [{
                        'type': 'MetadataOnly',
                        'source': 'system',
                        'content': f"Results too large to store (>{total_size/1024/1024:.1f}MB). Only metadata saved.",
                        'timestamp': datetime.now().isoformat(),
                        'original_result_count': len(results)
                    }],
                    'created_at': datetime.now().isoformat(),
                    'is_metadata_only': True,
                    'total_images': image_index
                }
                try:
                    container.create_item(minimal_document)
                    st.success(f"Metadata stored with ID: {run_id}")
                except Exception as e2:
                    st.error(f"Failed to store even metadata: {e2}")
            else:
                st.error(f"Failed to store run result: {e}")
    
    def load_run_result(self, run_id: str):
        """Load run result from Azure Cosmos DB."""
        if not self.storage_enabled:
            return None
        
        container = self.get_cosmos_client()
        if not container:
            return None
        
        try:
            document = container.read_item(item=run_id, partition_key=run_id)
            return document
        except Exception as e:
            st.error(f"Failed to load run result: {e}")
            return None


# Global instance for easy access
storage_manager = AzureStorageManager()
