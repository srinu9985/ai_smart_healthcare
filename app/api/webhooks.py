# # app/api/webhooks.py - EMMA Healthcare version
#
# from fastapi import APIRouter, Request, HTTPException, Response,Depends,BackgroundTasks
# from app.db.client import get_db
# from app.core.logger import logger
# from app.utils.helper_tools import process_transcript_and_fetch_exotel
#
# router = APIRouter(
#     prefix="/webhooks",
#     tags=["Webhooks"]
# )
#
# @router.post("/calls/transcriptions")
# async def call_end_webhook(
#     request: Request,
#     background_tasks: BackgroundTasks,
#     db=Depends(get_db)
# ):
#     """Webhook endpoint that responds immediately and processes in background"""
#     try:
#         data = await request.json()
#         call_data = data.get("call", {})
#         call_id = call_data["callId"]
#
#         if not call_id:
#             return {"message": "Invalid payload", "data_received": data}
#         print("data send to the background to process the tasks")
#         # Check if we need to fetch Exotel details
#         background_tasks.add_task(process_transcript_and_fetch_exotel, call_id, db)
#         return Response(status_code=204)
#
#     except Exception as e:
#         print(f"Error in webhook handler: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")
