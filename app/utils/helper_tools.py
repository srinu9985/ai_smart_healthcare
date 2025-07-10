# import httpx
# import time
# from datetime import datetime, timezone
# from requests.auth import HTTPBasicAuth
# from app.core.logger import logger
# import os
# import requests
# import xml.etree.ElementTree as ET
# from app.db.client import get_db
# from dotenv import load_dotenv
#
# load_dotenv()
# import ast
# from app.api.healthcare import create_patient_bot
# from app.models.healthcare_models import PatientCreate
# from pydantic import ValidationError
# from fastapi import HTTPException
# from typing import Dict, Any
# import openai
#
# ULTRAVOX_API_KEY = os.getenv("ULTRAVOX_API_KEY")
# openai.api_key = os.getenv("OPENAI_API_KEY")
#
#
# # processing the transcriptions of calls and calling the call_details function to fetch call details from exotel
# async def process_transcript_and_fetch_exotel(call_id: str, db):
#     """Process transcript data and fetch Exotel details if needed"""
#     try:
#         # Get call log (which should contain the Exotel call_sid)
#         call_log = db.healthcare_call_logs.find_one({"uvx_id": call_id})
#         if not call_log:
#             print(f"No call log for {call_id}")
#             return
#
#         # Check if we need to fetch Exotel recording URL
#         if not call_log.get("recording_url"):
#             call_sid = call_log.get("call_sid")
#             if call_sid:
#                 # Fetch Exotel details synchronously since it has its own retry logic
#                 success = fetch_call_details(call_sid)
#                 if not success:
#                     print(f"Failed to fetch Exotel details for call_sid {call_sid}")
#
#         # Get Ultravox transcript
#         async with httpx.AsyncClient() as client:
#             url = f"https://api.ultravox.ai/api/calls/{call_id}/messages"
#             headers = {"X-API-Key": ULTRAVOX_API_KEY}
#             response = await client.get(url, headers=headers)
#             response.raise_for_status()
#             messages_data = response.json()
#
#         messages = [
#             f"Role: {msg['role']}\nText: {msg.get('text', '')}\nCall Stage Index: {msg['callStageMessageIndex']}\n\n"
#             for msg in messages_data.get("results", [])
#         ]
#
#         call_record = {
#             "uvx_id": call_id,
#             # "appointment_id": appointment_id,
#             "messages": messages,
#             "created_at": datetime.now(timezone.utc)
#         }
#
#         db.call_transcripts.insert_one(call_record)
#
#         # result= await extract_patient_info_from_conversation(call_id, db)
#         result = await generate_report_from_transcript(call_id, db)
#
#         return "success"
#
#     except Exception as e:
#         print(f"Error processing transcript {call_id}: {str(e)}")
#
#
# # Fetching call details in exotel using callsid
# def fetch_call_details(call_sid):
#     print("called from webhook to get recording url")
#     account_sid = os.getenv("EXOTEL_ACCOUNT_SID")
#     api_key = os.getenv("EXOTEL_API_KEY")
#     api_token = os.getenv("EXOTEL_API_TOKEN")
#     subdomain = "api.exotel.com"
#
#     url = f"https://{subdomain}/v1/Accounts/{account_sid}/Calls/{call_sid}"
#
#     time.sleep(30)
#
#     for attempt in range(6):
#         try:
#             response = requests.get(url, auth=HTTPBasicAuth(api_key, api_token))
#
#             if response.status_code != 200:
#                 logger.warning(f"Attempt {attempt + 1}: Failed to fetch call details. Retrying in 5s...")
#                 time.sleep(5)
#                 continue
#
#             root = ET.fromstring(response.text)
#             call_elem = root.find('Call')
#
#             if call_elem is None:
#                 raise Exception("No <Call> element found in XML response.")
#
#             recording_url = call_elem.findtext('RecordingUrl')
#             duration = call_elem.findtext('Duration')
#             from_number = call_elem.findtext('From')
#             to_number = call_elem.findtext('To')
#             start_time = call_elem.findtext('StartTime')
#             end_time = call_elem.findtext('EndTime')
#             call_status = call_elem.findtext('Status')
#
#             if not recording_url:
#                 logger.warning(f"Attempt {attempt + 1}: Recording URL not available yet. Retrying in 5s...")
#                 time.sleep(5)
#                 continue
#             db = get_db()
#             db.healthcare_call_logs.update_one(
#                 {"call_sid": call_sid},
#                 {
#                     "$set": {
#                         "call_status": call_status,
#                         "from_number": from_number,
#                         "to_number": to_number,
#                         "start_time": start_time,
#                         "end_time": end_time,
#                         "recording_url": recording_url,
#                         "duration": int(duration) if duration else None,
#                         "created_at": datetime.now(timezone.utc)
#                     }
#                 }
#             )
#
#             logger.info(f"Successfully fetched details for call {call_sid}")
#             return True
#
#         except Exception as e:
#             logger.error(f"Attempt {attempt + 1}: Error fetching call details for {call_sid}: {str(e)}")
#             time.sleep(5)
#
#     logger.error(f"Failed to fetch call details after 5 attempts for {call_sid}")
#     return False
#
#
# # transcriptions functions
# # async def extract_patient_info_from_conversation(conversation: str) -> Dict[str, Any]:
# #     """
# #     Extract patient information from conversation using AI
# #     """
# #     try:
# #         prompt = f"""
# #         Given the following patient-receptionist conversation, extract a structured JSON object in the following dictionary format (do not wrap the dictionary in quotes):
# #
# #         {{
# #             "fullName": "string or null",
# #             "contactNumber": "string or null",
# #             "emergencyNumber": "string or null",
# #             "preferredLanguage": "string or null",
# #             "dateOfBirth": "YYYY-MM-DD or null",
# #             "age": "number or null",
# #             "gender": "Male/Female/Other or null",
# #             "currentAddress": "string or null",
# #             "permanentAddress": "string or null",
# #             "nationality": "string or null",
# #             "aadhaarNumber": "string or null",
# #             "registeredLocation": "string or null",
# #             "summary": "string or null"
# #         }}
# #
# #         Requirements:
# #         - Return only a valid Python dictionary (no string-wrapped JSON).
# #         - Ensure all keys are present with unique names.
# #         - Deduplicate any repeated information.
# #         - The "summary" field should be a concise but complete overview of the conversation between the patient and the receptionist.
# #
# #         Conversation:
# #         {conversation}
# #         """
# #         response = openai.ChatCompletion.create(
# #             model="gpt-4o-mini",
# #             messages=[{"role": "user", "content": prompt}],
# #             temperature=0.2
# #         )
# #         return response['choices'][0]['message']['content']
# #
# #     except Exception as e:
# #         logger.error(f"Error extracting patient info: {str(e)}")
# #         return {}
# #
# #
# # async def format_conversation(messages: list) -> str:
# #     """Format the conversation with speaker labels"""
# #     formatted = []
# #     for msg in messages:
# #         if "MESSAGE_ROLE_USER" in msg:
# #             text = msg.split("Text: ")[1].split("\nCall Stage Index:")[0].strip()
# #             formatted.append(f"patient: {text}")
# #         elif "MESSAGE_ROLE_AGENT" in msg:
# #             text = msg.split("Text: ")[1].split("\nCall Stage Index:")[0].strip()
# #             formatted.append(f"receptionist: {text}")
# #     return "\n".join(formatted)
# #
# #
# # async def generate_report_from_transcript(call_id: str, db):
# #     """Generate and store report for a call"""
# #     transcript = db.call_transcripts.find_one({"uvx_id": call_id})
# #     if not transcript:
# #         raise ValueError(f"No transcript found for callId: {call_id}")
# #
# #     appointment_id = transcript.get("appointment_id")
# #     if not appointment_id:
# #         print(f"No appointment_id in transcript for callId: {call_id}")
# #
# #     conversation = await format_conversation(transcript["messages"])
# #     print("conversation", conversation)
# #
# #     # Extract patient info from conversation
# #     report = await extract_patient_info_from_conversation(conversation)
# #     print("reporttt", report)
# #     # Convert report to dictionary if it's a string
# #     if isinstance(report, str):
# #         try:
# #             import json
# #             # Try JSON parsing first, then fall back to ast if needed
# #             report_dict = json.loads(report)
# #         except json.JSONDecodeError:
# #             try:
# #                 report_dict = ast.literal_eval(report)
# #             except (ValueError, SyntaxError) as e:
# #                 logger.error(f"Error converting report string: {e}")
# #                 report_dict = {}
# #     else:
# #         report_dict = report
# #
# #     print("Converted report dictionary:", report_dict, type(report_dict))
# #
# #     # Create PatientCreate object from the extracted data
# #     try:
# #         report_dict["uvx_id"] = call_id
# #         print("reportdcooo1223", report_dict)
# #         # Call the create_patient_bot function with the extracted  to save the patient data in patients collection
# #         # creation_result =await create_patient_bot(report_dict)
# #         db.healthcare_call_logs.update_one(
# #             {"uvx_id": call_id},
# #             {
# #                 "$set": {"call_summary": report_dict.get("summary")}
# #             }
# #         )
# #
# #         # Store the report in the database
# #         db.call_reports.insert_one({
# #             "uvx_id": call_id,
# #             # "appointment_id": appointment_id,
# #             "patient_info": report_dict,
# #             # "patient_creation_result": creation_result,
# #             "generated_at": datetime.now(timezone.utc)
# #         })
# #
# #         return {
# #             "patient_info": report_dict,
# #             # "creation_result": creation_result
# #         }
# #
# #     except ValidationError as e:
# #         logger.error(f"Validation error creating patient: {str(e)}")
# #         raise HTTPException(status_code=400, detail=f"Invalid patient data: {str(e)}")
# #     except Exception as e:
# #         logger.error(f"Error creating patient: {str(e)}")
# #         raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")
