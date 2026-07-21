from fastapi import APIRouter

from app.schemas.appointment import AppointmentRequest

from app.services.appointment_service import create_appointment

router = APIRouter()


@router.post("/appointments")
def book(request: AppointmentRequest):

    appointment = create_appointment(request)

    return {

        "success": True,

        "appointment_id": appointment.id,

        "message": "Your appointment request has been received. The clinic staff will contact you for confirmation."
    }