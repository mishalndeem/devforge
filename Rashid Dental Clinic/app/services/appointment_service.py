from app.database.database import SessionLocal
from app.database.models import Appointment


def create_appointment(data):

    db = SessionLocal()

    appointment = Appointment(

        name=data.name,

        phone=data.phone,

        email=data.email,

        preferred_date=data.preferred_date,

        message=data.message
    )

    db.add(appointment)

    db.commit()

    db.refresh(appointment)

    db.close()

    return appointment