from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ContactInquiry, CustomProjectRequest
from app.schemas import ContactIn, ContactOut, ProjectRequestIn, ProjectRequestOut
from app.security import rate_limit

router = APIRouter(prefix="/api", tags=["contact"])


@router.post(
    "/contact",
    response_model=ContactOut,
    status_code=201,
    dependencies=[Depends(rate_limit("contact_submit", 20, 600))],
)
def submit_contact(req: ContactIn, db: Session = Depends(get_db)):
    inquiry = ContactInquiry(
        name=req.name,
        email=req.email,
        phone=req.phone,
        company=req.company,
        subject=req.subject,
        message=req.message,
        service_type=req.service_type,
    )
    db.add(inquiry)
    db.commit()
    return ContactOut(message="Inquiry received. We will get back to you shortly.")


@router.post(
    "/custom-project-request",
    response_model=ProjectRequestOut,
    status_code=201,
    dependencies=[Depends(rate_limit("project_request_submit", 20, 600))],
)
def submit_project_request(req: ProjectRequestIn, db: Session = Depends(get_db)):
    project_request = CustomProjectRequest(
        name=req.name,
        email=req.email,
        phone=req.phone,
        company=req.company,
        project_type=req.project_type,
        budget_range=req.budget_range,
        timeline=req.timeline,
        description=req.description,
    )
    db.add(project_request)
    db.commit()
    return ProjectRequestOut(
        message="Project request submitted. We will review and contact you."
    )
