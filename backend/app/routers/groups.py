from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import UserGroup, GroupMember, SteamUser
from app.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupDetailResponse,
    GroupMemberAdd, GroupMemberResponse, SteamUserResponse
)
from app.services.data_service import GroupService, ComparisonService

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("/", response_model=GroupResponse)
def create_group(
    group_data: GroupCreate,
    created_by_steam_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new group."""
    created_by = None
    if created_by_steam_id:
        user = db.query(SteamUser).filter(
            SteamUser.steam_id == created_by_steam_id
        ).first()
        if user:
            created_by = user.id
    
    group_service = GroupService(db)
    group = group_service.create_group(
        name=group_data.name,
        description=group_data.description,
        created_by=created_by
    )
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=0
    )


@router.get("/", response_model=List[GroupResponse])
def get_all_groups(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all groups."""
    groups = db.query(UserGroup).offset(skip).limit(limit).all()
    
    results = []
    for group in groups:
        member_count = db.query(func.count(GroupMember.id)).filter(
            GroupMember.group_id == group.id
        ).scalar()
        
        results.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            updated_at=group.updated_at,
            member_count=member_count
        ))
    
    return results


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(group_id: UUID, db: Session = Depends(get_db)):
    """Get group details with members."""
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get members
    members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id
    ).all()
    
    member_responses = []
    for member in members:
        user = db.query(SteamUser).filter(
            SteamUser.id == member.steam_user_id
        ).first()
        if user:
            member_responses.append(GroupMemberResponse(
                id=member.id,
                steam_user=user,
                added_at=member.added_at
            ))
    
    # Get creator
    creator = None
    if group.created_by:
        creator = db.query(SteamUser).filter(
            SteamUser.id == group.created_by
        ).first()
    
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=len(member_responses),
        members=member_responses,
        creator=creator
    )


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: UUID,
    group_data: GroupUpdate,
    db: Session = Depends(get_db)
):
    """Update a group."""
    group_service = GroupService(db)
    group = group_service.update_group(
        group_id=group_id,
        name=group_data.name,
        description=group_data.description
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    member_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group_id
    ).scalar()
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=member_count
    )


@router.delete("/{group_id}")
def delete_group(group_id: UUID, db: Session = Depends(get_db)):
    """Delete a group."""
    group_service = GroupService(db)
    if not group_service.delete_group(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {"message": "Group deleted successfully"}


@router.post("/{group_id}/members")
async def add_members(
    group_id: UUID,
    member_data: GroupMemberAdd,
    db: Session = Depends(get_db)
):
    """Add members to a group by Steam IDs."""
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group_service = GroupService(db)
    added_members = await group_service.add_members(group_id, member_data.steam_ids)
    
    return {
        "message": f"Added {len(added_members)} members to group",
        "added_count": len(added_members)
    }


@router.delete("/{group_id}/members/{user_id}")
def remove_member(
    group_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove a member from a group."""
    group_service = GroupService(db)
    if not group_service.remove_member(group_id, user_id):
        raise HTTPException(status_code=404, detail="Member not found in group")
    
    return {"message": "Member removed successfully"}


@router.get("/{group_id}/comparison")
def get_group_comparison(group_id: UUID, db: Session = Depends(get_db)):
    """Get comparison data for all members in a group."""
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group_service = GroupService(db)
    comparison_service = ComparisonService(db)
    
    members = group_service.get_group_members(group_id)
    member_ids = [m.id for m in members]
    
    comparison = comparison_service.compare_users(member_ids)
    
    return {
        "group": GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            updated_at=group.updated_at,
            member_count=len(members)
        ),
        "comparison": comparison
    }


@router.get("/{group_id}/game-intersection")
def get_game_intersection(group_id: UUID, db: Session = Depends(get_db)):
    """Get games with highest ownership intersection in a group."""
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    comparison_service = ComparisonService(db)
    intersection = comparison_service.get_game_intersection(group_id)
    
    return intersection


@router.post("/{group_id}/sync")
async def sync_group_users(
    group_id: UUID,
    db: Session = Depends(get_db)
):
    """Sync all users in a group."""
    from app.services.data_service import DataSyncService
    
    group_service = GroupService(db)
    members = group_service.get_group_members(group_id)
    
    if not members:
        raise HTTPException(status_code=404, detail="Group has no members")
    
    sync_service = DataSyncService(db)
    results = []
    
    for member in members:
        try:
            await sync_service.sync_user_profile(member.steam_id)
            await sync_service.sync_user_games(member.steam_id)
            results.append({"steam_id": member.steam_id, "status": "success"})
        except Exception as e:
            results.append({"steam_id": member.steam_id, "status": "error", "error": str(e)})
    
    return {
        "message": "Group sync complete",
        "results": results
    }
