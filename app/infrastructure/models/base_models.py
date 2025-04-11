from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

class MetadataModel(BaseModel):
    source: str = ''
    # Status
    is_deleted: bool = False
    is_processed: bool = False
    # Timestamp
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = datetime.now(timezone.utc)
    processed_timestamp: Optional[datetime] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }