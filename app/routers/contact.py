from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ContactInquiry, CustomProjectRequest
from app.schemas import ContactIn, ContactOut, ProjectRequestIn, ProjectRequestOut

router = APIRouter(prefix="/api", tags=["contact"])


@router.post("/contact", response_model=ContactOut, status_code=201)
def submit_contact(req: ContactIn, db: Session = Depends(get_db)):
    db.add(ContactInquiry(
        name=req.name,
        email=req.email,
        phone=req.phone,
        company=req.company,
        subject=req.subject,
        message=req.message,
        service_type=req.service_type,
    ))
    return ContactOut(message="Inquiry received. We will get back to you shortly.")


@router.post("/custom-project-request", response_model=ProjectRequestOut, status_code=201)
def submit_project_request(req: ProjectRequestIn, db: Session = Depends(get_db)):
    db.add(CustomProjectRequest(
        name=req.name,
        email=req.email,
        phone=req.phone,
        company=req.company,
        project_type=req.project_type,
        budget_range=req.budget_range,
        timeline=req.timeline,
        description=req.description,
    ))
    return ProjectRequestOut(
        message="Project request submitted. We will review and contact you."
    )
