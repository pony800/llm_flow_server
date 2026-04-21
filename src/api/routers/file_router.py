from fastapi import APIRouter, Query
from src.api.controllers import file_controller
from src.api.schemas.response.vo import PathTreeVO
from src.models.enums.com_enum import FileType

router = APIRouter(tags=["文件管理"])

@router.get("/file/tree", response_model=PathTreeVO)
async def file_tree(file_type: FileType = Query(...)):
    return await file_controller.get_file_tree(file_type=file_type)