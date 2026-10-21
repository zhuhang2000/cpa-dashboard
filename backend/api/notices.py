"""Important notices: every signed-in user reads them; admins publish, edit and delete."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, json_body, require_admin, require_user
from services import notices

router = APIRouter(tags=["notices"])


@router.get("/api/notices", dependencies=[Depends(require_user)])
def list_notices(conn=Depends(get_connection)):
    return notices.list_notices(conn)


@router.post("/api/admin/notices")
def create_notice(
    admin=Depends(require_admin), body=Depends(json_body), conn=Depends(get_connection)
):
    return notices.create_notice(conn, admin["id"], body)


@router.put("/api/admin/notices/{notice_id}", dependencies=[Depends(require_admin)])
def update_notice(notice_id: int, body=Depends(json_body), conn=Depends(get_connection)):
    return notices.update_notice(conn, notice_id, body)


@router.delete("/api/admin/notices/{notice_id}", dependencies=[Depends(require_admin)])
def delete_notice(notice_id: int, conn=Depends(get_connection)):
    return notices.delete_notice(conn, notice_id)
