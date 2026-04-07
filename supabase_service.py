"""
Supabase service for user management and storage.
Handles authentication, user management, and service usage tracking.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from gotrue.errors import AuthError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SupabaseService:
    """Service class for handling Supabase operations with local fallback"""

    def __init__(self):
        """Initialize Supabase client or fallback to local storage"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None
        self.use_local_storage = False

        # Check if Supabase is configured
        if not self.supabase_url or not self.supabase_key or \
           self.supabase_url.startswith("https://your-") or \
           self.supabase_key.startswith("your-"):
            logger.warning(
                "Supabase not configured. Using local storage fallback (SQLite + FAISS)."
            )
            self.use_local_storage = True
            from local_storage import get_local_storage
            self.local = get_local_storage()
            return

        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e}. Using local storage fallback.")
            self.use_local_storage = True
            from local_storage import get_local_storage
            self.local = get_local_storage()

    def _check_client(self):
        """Check if Supabase client is available"""
        if not self.client and not self.use_local_storage:
            raise ValueError("Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")

    # Authentication Methods
    async def sign_up(
        self, email: str, password: str, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        self._check_client()
        """
        Sign up a new user

        Args:
            email: User email
            password: User password
            metadata: Optional user metadata

        Returns:
            Dict containing user data and session info
        """
        try:
            response = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": metadata} if metadata else {},
                }
            )

            if response.user:
                logger.info(f"User signed up successfully: {email}")
                return {
                    "success": True,
                    "user": response.user,
                    "session": response.session,
                    "message": "User created successfully",
                }
            else:
                return {"success": False, "message": "Failed to create user"}

        except AuthError as e:
            logger.error(f"Sign up error: {e}")
            return {"success": False, "message": str(e)}

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in an existing user

        Args:
            email: User email
            password: User password

        Returns:
            Dict containing user data and session info
        """
        self._check_client()
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if response.user:
                logger.info(f"User signed in successfully: {email}")
                result = {
                    "success": True,
                    "user": response.user,
                    "session": response.session,
                }

                # Add tokens if session exists
                if response.session:
                    result["access_token"] = response.session.access_token
                    result["refresh_token"] = response.session.refresh_token

                return result
            else:
                return {"success": False, "message": "Invalid credentials"}

        except AuthError as e:
            logger.error(f"Sign in error: {e}")
            return {"success": False, "message": str(e)}

    async def sign_out(self) -> Dict[str, Any]:
        """Sign out current user"""
        self._check_client()
        try:
            self.client.auth.sign_out()
            logger.info("User signed out successfully")
            return {"success": True, "message": "User signed out successfully"}
        except AuthError as e:
            logger.error(f"Sign out error: {e}")
            return {"success": False, "message": str(e)}

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        self._check_client()
        try:
            user = self.client.auth.get_user()
            if user and user.user:
                return {"success": True, "user": user.user}
            return None
        except AuthError as e:
            logger.error(f"Get user error: {e}")
            return None

    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh user session"""
        self._check_client()
        try:
            response = self.client.auth.refresh_session(refresh_token)
            result = {
                "success": True,
                "session": response.session,
            }

            # Add tokens if session exists
            if response.session:
                result["access_token"] = response.session.access_token
                result["refresh_token"] = response.session.refresh_token

            return result
        except AuthError as e:
            logger.error(f"Refresh session error: {e}")
            return {"success": False, "message": str(e)}

    # User Management Methods
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database"""
        self._check_client()
        try:
            response = (
                self.client.table("user_profiles")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if response.data:
                return response.data
            return None
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            return None

    async def create_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create user profile in database"""
        self._check_client()
        try:
            profile_data["user_id"] = user_id
            profile_data["created_at"] = datetime.now(timezone.utc).isoformat()

            response = self.client.table("user_profiles").insert(profile_data).execute()

            if response.data:
                logger.info(f"User profile created for user: {user_id}")
                return {"success": True, "profile": response.data[0]}
            return {"success": False, "message": "Failed to create user profile"}
        except Exception as e:
            logger.error(f"Create user profile error: {e}")
            return {"success": False, "message": str(e)}

    async def update_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user profile in database"""
        self._check_client()
        try:
            profile_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                self.client.table("user_profiles")
                .update(profile_data)
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                logger.info(f"User profile updated for user: {user_id}")
                return {"success": True, "profile": response.data[0]}
            return {"success": False, "message": "Failed to update user profile"}
        except Exception as e:
            logger.error(f"Update user profile error: {e}")
            return {"success": False, "message": str(e)}

    # Service Usage Tracking Methods
    async def create_service_record(
        self,
        user_id: str,
        file_names: List[str],
        ai_response: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a service usage record

        Args:
            user_id: User ID
            file_names: List of uploaded file names
            ai_response: AI response data
            metadata: Optional metadata (file sizes, processing time, etc.)

        Returns:
            Dict containing the created record
        """
        if not self.client:
            logger.warning("Supabase not configured. Service record not saved.")
            return {"success": False, "message": "Supabase not configured"}
        try:
            record_data = {
                "user_id": user_id,
                "file_names": file_names,
                "ai_response": ai_response,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            response = (
                self.client.table("service_usage_records").insert(record_data).execute()
            )

            if response.data:
                logger.info(f"Service record created for user: {user_id}")
                return {"success": True, "record": response.data[0]}
            return {"success": False, "message": "Failed to create service record"}
        except Exception as e:
            logger.error(f"Create service record error: {e}")
            return {"success": False, "message": str(e)}

    async def get_user_service_records(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's service usage records"""
        self._check_client()
        try:
            response = (
                self.client.table("service_usage_records")
                .select("file_names, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )

            return response.data or []
        except Exception as e:
            logger.error(f"Get user service records error: {e}")
            return []

    async def get_service_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific service record"""
        self._check_client()
        try:
            response = (
                self.client.table("service_usage_records")
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Get service record error: {e}")
            return None

    async def update_service_record(
        self, record_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a service record"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                self.client.table("service_usage_records")
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )

            if response.data:
                return {"success": True, "record": response.data[0]}
            return {"success": False, "message": "Failed to update service record"}
        except Exception as e:
            logger.error(f"Update service record error: {e}")
            return {"success": False, "message": str(e)}

    async def delete_service_record(
        self, record_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Delete a service record (only by the owner)"""
        self._check_client()
        try:
            response = (
                self.client.table("service_usage_records")
                .delete()
                .eq("id", record_id)
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                return {
                    "success": True,
                    "message": "Service record deleted successfully",
                }
            return {
                "success": False,
                "message": "Failed to delete service record or record not found",
            }
        except Exception as e:
            logger.error(f"Delete service record error: {e}")
            return {"success": False, "message": str(e)}

    # Analytics and Statistics Methods
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user usage statistics"""
        self._check_client()
        try:
            # Get total records count
            total_records = (
                self.client.table("service_usage_records")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            # Get records from last 30 days
            thirty_days_ago = datetime.now(timezone.utc).replace(day=1).isoformat()
            recent_records = (
                self.client.table("service_usage_records")
                .select("*")
                .eq("user_id", user_id)
                .gte("created_at", thirty_days_ago)
                .execute()
            )

            # Calculate statistics
            total_files_processed = 0
            if recent_records.data:
                for record in recent_records.data:
                    total_files_processed += len(record.get("file_names", []))

            return {
                "total_records": len(total_records.data) if total_records.data else 0,
                "records_last_30_days": len(recent_records.data)
                if recent_records.data
                else 0,
                "total_files_processed_last_30_days": total_files_processed,
                "last_activity": recent_records.data[0]["created_at"]
                if recent_records.data
                else None,
            }
        except Exception as e:
            logger.error(f"Get user statistics error: {e}")
            return {
                "total_records": 0,
                "records_last_30_days": 0,
                "total_files_processed_last_30_days": 0,
                "last_activity": None,
            }

    # Document Management Methods
    async def create_document(
        self,
        user_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a document record"""
        if self.use_local_storage:
            return await self.local.create_document(user_id, file_name, file_type, file_size, file_path, metadata)
        
        self._check_client()
        try:
            document_data = {
                "user_id": user_id,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "original_file_path": file_path,
                "status": "processing",
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            response = self.client.table("documents").insert(document_data).execute()

            if response.data:
                logger.info(f"Document created: {file_name} for user: {user_id}")
                return {"success": True, "document": response.data[0]}
            return {"success": False, "message": "Failed to create document"}
        except Exception as e:
            logger.error(f"Create document error: {e}")
            return {"success": False, "message": str(e)}

    async def update_document_status(
        self, document_id: str, status: str, total_chunks: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update document processing status"""
        if self.use_local_storage:
            return await self.local.update_document_status(document_id, status, total_chunks)
        
        self._check_client()
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if total_chunks is not None:
                update_data["total_chunks"] = total_chunks

            response = (
                self.client.table("documents")
                .update(update_data)
                .eq("id", document_id)
                .execute()
            )

            if response.data:
                return {"success": True, "document": response.data[0]}
            return {"success": False, "message": "Failed to update document"}
        except Exception as e:
            logger.error(f"Update document status error: {e}")
            return {"success": False, "message": str(e)}

    async def get_user_documents(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's documents"""
        if self.use_local_storage:
            return await self.local.get_user_documents(user_id, limit, offset)
        
        self._check_client()
        try:
            response = (
                self.client.table("documents")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Get user documents error: {e}")
            return []

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document"""
        if self.use_local_storage:
            return await self.local.get_document(document_id)
        
        self._check_client()
        try:
            response = (
                self.client.table("documents")
                .select("*")
                .eq("id", document_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Get document error: {e}")
            return None

    async def delete_document(
        self, document_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Delete a document and its chunks"""
        if self.use_local_storage:
            return await self.local.delete_document(document_id, user_id)
        
        self._check_client()
        try:
            # Chunks will be deleted automatically via CASCADE
            response = (
                self.client.table("documents")
                .delete()
                .eq("id", document_id)
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                return {"success": True, "message": "Document deleted successfully"}
            return {"success": False, "message": "Document not found"}
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            return {"success": False, "message": str(e)}

    # Chunk Storage Methods
    async def store_chunks(
        self, chunks_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store multiple document chunks with embeddings"""
        if self.use_local_storage:
            return await self.local.store_chunks(chunks_data)
        
        self._check_client()
        try:
            if not chunks_data:
                return {"success": True, "chunks": []}

            response = (
                self.client.table("document_chunks").insert(chunks_data).execute()
            )

            if response.data:
                logger.info(f"Stored {len(response.data)} chunks")
                return {"success": True, "chunks": response.data}
            return {"success": False, "message": "Failed to store chunks"}
        except Exception as e:
            logger.error(f"Store chunks error: {e}")
            return {"success": False, "message": str(e)}

    async def get_document_chunks(
        self, document_id: str
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        if self.use_local_storage:
            return await self.local.get_document_chunks(document_id)
        
        self._check_client()
        try:
            response = (
                self.client.table("document_chunks")
                .select("*")
                .eq("document_id", document_id)
                .order("chunk_index")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Get document chunks error: {e}")
            return []

    async def store_insights(self, insights_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store traceable insights in database."""
        if self.use_local_storage:
            return await self.local.store_insights(insights_data)

        self._check_client()
        try:
            if not insights_data:
                return {"success": True, "insights": []}

            valid_rows = [
                r for r in insights_data
                if isinstance(r.get("source_pages"), list) and len(r.get("source_pages", [])) > 0
            ]
            if not valid_rows:
                return {"success": True, "insights": []}

            response = self.client.table("insights").upsert(valid_rows).execute()
            return {"success": True, "insights": response.data or []}
        except Exception as e:
            logger.error(f"Store insights error: {e}")
            return {"success": False, "message": str(e)}

    async def get_insight(self, insight_id: str, document_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get one persisted insight by insight_id."""
        if self.use_local_storage:
            return await self.local.get_insight(insight_id, document_id)

        self._check_client()
        try:
            q = self.client.table("insights").select("*").eq("insight_id", insight_id)
            if document_id:
                q = q.eq("document_id", document_id)
            response = q.limit(1).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Get insight error: {e}")
            return None

    async def store_rig_summaries(self, summaries_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store group/rig summaries for report synthesis without vector retrieval."""
        if self.use_local_storage:
            return await self.local.store_rig_summaries(summaries_data)

        self._check_client()
        try:
            if not summaries_data:
                return {"success": True, "summaries": []}

            valid_rows = [
                r for r in summaries_data
                if isinstance(r.get("source_pages"), list) and len(r.get("source_pages", [])) > 0
            ]
            if not valid_rows:
                return {"success": True, "summaries": []}

            response = self.client.table("rig_summaries").upsert(valid_rows).execute()
            return {"success": True, "summaries": response.data or []}
        except Exception as e:
            logger.error(f"Store rig summaries error: {e}")
            return {"success": False, "message": str(e)}

    async def get_rig_summaries(self, document_id: str) -> List[Dict[str, Any]]:
        """Get rig summaries for a document."""
        if self.use_local_storage:
            return await self.local.get_rig_summaries(document_id)

        self._check_client()
        try:
            response = (
                self.client.table("rig_summaries")
                .select("*")
                .eq("document_id", document_id)
                .order("created_at")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Get rig summaries error: {e}")
            return []

    # Vector Search Methods
    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        match_threshold: float = 0.5,
        match_count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        if self.use_local_storage:
            return await self.local.search_similar_chunks(query_embedding, user_id, match_threshold, match_count)
        
        self._check_client()
        try:
            # Call the PostgreSQL function
            response = self.client.rpc(
                "search_similar_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": match_count,
                    "filter_user_id": user_id,
                },
            ).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"Search similar chunks error: {e}")
            return []

    # Storage Methods (for file uploads)
    async def upload_file_to_storage(
        self, user_id: str, file_path: str, file_content: bytes, file_name: str
    ) -> Dict[str, Any]:
        """Upload a file to Supabase Storage"""
        if self.use_local_storage:
            return await self.local.upload_file_to_storage(user_id, file_path, file_content, file_name)
        
        self._check_client()
        try:
            # Path: user_id/filename
            storage_path = f"{user_id}/{file_name}"

            response = self.client.storage.from_("documents").upload(
                storage_path, file_content
            )

            if response:
                logger.info(f"File uploaded to storage: {storage_path}")
                return {"success": True, "path": storage_path}
            return {"success": False, "message": "Failed to upload file"}
        except Exception as e:
            logger.error(f"Upload file to storage error: {e}")
            return {"success": False, "message": str(e)}

    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get signed URL for a file in storage"""
        self._check_client()
        try:
            response = self.client.storage.from_("documents").create_signed_url(
                file_path, expires_in
            )
            return response.get("signedURL") if response else None
        except Exception as e:
            logger.error(f"Get file URL error: {e}")
            return None

    async def delete_file_from_storage(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from storage"""
        self._check_client()
        try:
            response = self.client.storage.from_("documents").remove([file_path])
            if response:
                return {"success": True, "message": "File deleted from storage"}
            return {"success": False, "message": "Failed to delete file"}
        except Exception as e:
            logger.error(f"Delete file from storage error: {e}")
            return {"success": False, "message": str(e)}

    # Database Helper Methods
    async def initialize_database(self) -> Dict[str, Any]:
        """Initialize database tables if they don't exist"""
        self._check_client()
        try:
            # This would typically be handled by Supabase migrations
            # But we can check if tables exist and provide helpful error messages

            # Test user_profiles table
            try:
                self.client.table("user_profiles").select("id").limit(1).execute()
            except Exception:
                logger.warning("user_profiles table might not exist")

            # Test service_usage_records table
            try:
                self.client.table("service_usage_records").select("id").limit(
                    1
                ).execute()
            except Exception:
                logger.warning("service_usage_records table might not exist")

            # Test documents table
            try:
                self.client.table("documents").select("id").limit(1).execute()
            except Exception:
                logger.warning("documents table might not exist - run supabase_schema.sql")

            # Test document_chunks table
            try:
                self.client.table("document_chunks").select("id").limit(1).execute()
            except Exception:
                logger.warning("document_chunks table might not exist - run supabase_schema.sql")

            # Test insights table
            try:
                self.client.table("insights").select("id").limit(1).execute()
            except Exception:
                logger.warning("insights table might not exist - run supabase_schema.sql")

            # Test rig_summaries table
            try:
                self.client.table("rig_summaries").select("id").limit(1).execute()
            except Exception:
                logger.warning("rig_summaries table might not exist - run supabase_schema.sql")

            return {"success": True, "message": "Database check completed"}
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return {"success": False, "message": str(e)}


# Global service instance
supabase_service = SupabaseService()


# Convenience functions for easy access
async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Convenience function to authenticate user"""
    return await supabase_service.sign_in(email, password)


async def create_user(
    email: str, password: str, metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Convenience function to create user"""
    return await supabase_service.sign_up(email, password, metadata)


async def log_service_usage(
    user_id: str,
    file_names: List[str],
    ai_response: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function to log service usage"""
    return await supabase_service.create_service_record(
        user_id, file_names, ai_response, metadata
    )


async def get_user_history(
    user_id: str, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Convenience function to get user history"""
    return await supabase_service.get_user_service_records(user_id, limit, offset)


if __name__ == "__main__":
    # Test the service
    async def test_service():
        try:
            # Initialize database
            result = await supabase_service.initialize_database()
            print("Database initialization:", result)

            # Test authentication (you would use real credentials)
            # auth_result = await authenticate_user("test@example.com", "password123")
            # print("Authentication test:", auth_result)

        except Exception as e:
            print(f"Test error: {e}")

    # Run test
    asyncio.run(test_service())
