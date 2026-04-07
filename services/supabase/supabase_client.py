"""
FastAPI integration with Supabase authentication and service usage tracking.
This example shows how to integrate the Supabase service with your existing FastAPI application.
"""

from fastapi import HTTPException, Depends, Form, APIRouter, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from gotrue import User
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import jwt
import time

from services.supabase.supabase_service import supabase_service
from services.vector_store.indexing.vector_storage import get_vector_service

# Security
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Create routers
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
user_router = APIRouter(prefix="/user", tags=["user"])
history_router = APIRouter(prefix="/history", tags=["history"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])
search_router = APIRouter(prefix="/search", tags=["search"])


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Get current user from JWT token"""
    try:
        # Extract the JWT token from the Authorization header
        jwt_token = credentials.credentials

        # Set the session with the provided JWT token
        try:
            # Parse and verify the JWT token
            supabase_service.client.auth.set_session(jwt_token, jwt_token)

            # Get the current user from the token
            user_response = supabase_service.client.auth.get_user()

            if user_response and user_response.user:
                return user_response.user
            else:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

        except Exception:
            # If setting session fails, try to get user directly from JWT
            try:
                # Alternative approach: manually decode JWT to get user info

                # Decode JWT without verification for user info (Supabase handles verification)
                decoded_token = jwt.decode(
                    jwt_token, options={"verify_signature": False}
                )

                # Check if token has expired
                if decoded_token.get("exp", 0) < time.time():
                    raise HTTPException(status_code=401, detail="Token has expired")

                # Get user ID from token
                user_id = decoded_token.get("sub")
                if not user_id:
                    raise HTTPException(
                        status_code=401, detail="Invalid token: missing user ID"
                    )

                return User(
                    id=user_id,
                    email=decoded_token.get("email"),
                    user_metadata=decoded_token.get("user_metadata", {}),
                    app_metadata=decoded_token.get("app_metadata", {}),
                    aud=decoded_token.get("aud", []),
                    created_at=decoded_token.get("created_at", None),
                    updated_at=decoded_token.get("updated_at", None),
                )

            except Exception as jwt_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Token verification failed: {str(jwt_error)}",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# Optional dependency for authenticated routes
async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(optional_security),
):
    """Get current user optionally (for routes that work with or without auth)"""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Authentication endpoints
@auth_router.post("/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(None),
):
    """Sign up a new user"""
    try:
        # Prepare metadata
        metadata = {}
        if name:
            metadata["full_name"] = name

        # Create user
        result = await supabase_service.sign_up(email, password, metadata)

        if result["success"]:
            return {
                "message": "User created successfully",
                "user": result["user"],
                "requires_verification": True,
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@auth_router.post("/signin")
async def signin(email: str = Form(...), password: str = Form(...)):
    """Sign in an existing user"""
    try:
        result = await supabase_service.sign_in(email, password)

        if result["success"]:
            return {
                "message": "User signed in successfully",
                "user": result["user"],
                "access_token": result.get("access_token"),
                "token_type": "bearer",
            }
        else:
            raise HTTPException(status_code=401, detail=result["message"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signin failed: {str(e)}")


@auth_router.post("/signout")
async def signout(current_user=Depends(get_current_user)):
    """Sign out current user"""
    try:
        await supabase_service.sign_out()
        return {"message": "User signed out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signout failed: {str(e)}")


# User profile endpoints
@user_router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    """Get current user's profile"""
    try:
        profile = await supabase_service.get_user_profile(current_user.id)

        if profile:
            return profile
        else:
            raise HTTPException(status_code=404, detail="Profile not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@user_router.put("/profile")
async def update_profile(
    current_user=Depends(get_current_user),
    full_name: str = Form(None),
    bio: str = Form(None),
    company: str = Form(None),
    location: str = Form(None),
    website: str = Form(None),
):
    """Update current user's profile"""
    try:
        profile_data = {}
        if full_name is not None:
            profile_data["full_name"] = full_name
        if bio is not None:
            profile_data["bio"] = bio
        if company is not None:
            profile_data["company"] = company
        if location is not None:
            profile_data["location"] = location
        if website is not None:
            profile_data["website"] = website

        result = await supabase_service.update_user_profile(
            current_user.id, profile_data
        )

        if result["success"]:
            return result["profile"]
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update profile: {str(e)}"
        )


@user_router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current user information"""
    return {"user_id": current_user.id, "email": current_user.email}


# History and analytics endpoints
@history_router.get("/")
async def get_history(
    current_user=Depends(get_current_user), limit: int = 50, offset: int = 0
):
    """Get user's processing history"""
    try:
        records = await supabase_service.get_user_service_records(
            current_user.id, limit, offset
        )

        return {"records": records, "count": len(records)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@history_router.get("/{record_id}")
async def get_record(record_id: str, current_user=Depends(get_current_user)):
    """Get a specific service record"""
    try:
        record = await supabase_service.get_service_record(record_id)

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if user owns this record
        if record.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return record

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get record: {str(e)}")


@history_router.delete("/{record_id}")
async def delete_record(record_id: str, current_user=Depends(get_current_user)):
    """Delete a specific service record"""
    try:
        result = await supabase_service.delete_service_record(
            record_id, current_user.id
        )

        if result["success"]:
            return {"message": "Record deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete record: {str(e)}"
        )


@analytics_router.get("/")
async def get_analytics(current_user=Depends(get_current_user)):
    """Get user analytics and statistics"""
    try:
        stats = await supabase_service.get_user_statistics(current_user.id)

        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "statistics": stats,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get analytics: {str(e)}"
        )


@analytics_router.get("/summary")
async def get_user_stats_summary(current_user=Depends(get_current_user)):
    """Get a summary of user statistics"""
    try:
        stats = await supabase_service.get_user_statistics(current_user.id)

        return {
            "user_id": current_user.id,
            "summary": {
                "total_requests": stats.get("total_records", 0),
                "recent_activity": stats.get("records_last_30_days", 0),
                "files_processed": stats.get("total_files_processed_last_30_days", 0),
                "last_used": stats.get("last_activity"),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Test endpoint
@auth_router.get("/test/supabase")
async def test_supabase_connection():
    """Test Supabase connection and configuration"""
    try:
        # Test database connectivity
        result = await supabase_service.initialize_database()

        return {
            "supabase_connection": "successful",
            "database_check": result.get("message", "completed"),
            "url_configured": bool(supabase_service.supabase_url),
            "key_configured": bool(supabase_service.supabase_key),
        }
    except Exception as e:
        return {
            "supabase_connection": "failed",
            "error": str(e),
            "url_configured": bool(supabase_service.supabase_url),
            "key_configured": bool(supabase_service.supabase_key),
        }


# ============================================
# DOCUMENTS ENDPOINTS
# ============================================

class SearchRequest(BaseModel):
    """Request model for semantic search"""
    query: str
    match_threshold: Optional[float] = 0.5
    match_count: Optional[int] = 10


@documents_router.get("/")
async def get_user_documents(
    current_user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all documents for the current user"""
    try:
        documents = await supabase_service.get_user_documents(
            current_user.id, limit, offset
        )
        return {
            "documents": documents,
            "count": len(documents),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@documents_router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user=Depends(get_current_user)
):
    """Get a specific document with its chunks"""
    try:
        document = await supabase_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify ownership
        if document.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get chunks
        chunks = await supabase_service.get_document_chunks(document_id)
        
        return {
            "document": document,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@documents_router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a document and all its chunks"""
    try:
        result = await supabase_service.delete_document(
            document_id, current_user.id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


@documents_router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    current_user=Depends(get_current_user)
):
    """Get all chunks for a specific document"""
    try:
        # Verify document ownership
        document = await supabase_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get chunks
        chunks = await supabase_service.get_document_chunks(document_id)
        
        return {
            "document_id": document_id,
            "chunks": chunks,
            "total": len(chunks)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chunks: {str(e)}"
        )


# ============================================
# SEMANTIC SEARCH ENDPOINTS
# ============================================

@search_router.post("/")
async def search_chunks(
    search_request: SearchRequest,
    current_user=Depends(get_current_user)
):
    """Search for similar document chunks using semantic search"""
    try:
        # Generate embedding for the query
        vector_service = get_vector_service()
        query_embedding = vector_service.generate_query_embedding(search_request.query)
        
        # Search for similar chunks
        results = await supabase_service.search_similar_chunks(
            query_embedding=query_embedding,
            user_id=current_user.id,
            match_threshold=search_request.match_threshold,
            match_count=search_request.match_count
        )
        
        return {
            "query": search_request.query,
            "results": results,
            "total": len(results),
            "threshold": search_request.match_threshold
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@search_router.get("/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    current_user=Depends(get_current_user),
    match_count: int = Query(5, ge=1, le=20)
):
    """Find documents similar to a given document"""
    try:
        # Get the document and verify ownership
        document = await supabase_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get chunks from the document
        chunks = await supabase_service.get_document_chunks(document_id)
        
        if not chunks:
            return {
                "document_id": document_id,
                "similar_documents": [],
                "message": "No chunks found for this document"
            }
        
        # Use the first chunk as the query (or average of embeddings)
        first_chunk = chunks[0]
        query_embedding = first_chunk.get("embedding")
        
        if not query_embedding:
            raise HTTPException(
                status_code=400,
                detail="Document chunks don't have embeddings"
            )
        
        # Search for similar chunks
        results = await supabase_service.search_similar_chunks(
            query_embedding=query_embedding,
            user_id=current_user.id,
            match_threshold=0.7,
            match_count=match_count * 5  # Get more to filter by document
        )
        
        # Group by document_id and exclude the source document
        similar_docs: Dict[str, Dict[str, Any]] = {}
        for result in results:
            result_doc_id = result.get("document_id")
            
            # Skip the source document
            if result_doc_id == document_id:
                continue
            
            if result_doc_id not in similar_docs:
                similar_docs[result_doc_id] = {
                    "document_id": result_doc_id,
                    "file_name": result.get("file_name"),
                    "max_similarity": result.get("similarity", 0),
                    "matching_chunks": 1
                }
            else:
                similar_docs[result_doc_id]["matching_chunks"] += 1
                similar_docs[result_doc_id]["max_similarity"] = max(
                    similar_docs[result_doc_id]["max_similarity"],
                    result.get("similarity", 0)
                )
        
        # Sort by similarity and limit results
        similar_list = sorted(
            similar_docs.values(),
            key=lambda x: x["max_similarity"],
            reverse=True
        )[:match_count]
        
        return {
            "document_id": document_id,
            "file_name": document.get("file_name"),
            "similar_documents": similar_list,
            "total": len(similar_list)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar documents: {str(e)}"
        )
