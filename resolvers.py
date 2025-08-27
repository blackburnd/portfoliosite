# GraphQL resolvers and schema definition
import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from database import PortfolioDatabase


@strawberry.type
class Portfolio:
    id: str
    name: str
    title: str
    bio: str
    tagline: Optional[str] = None
    profile_image: Optional[str] = None
    email: str
    phone: Optional[str] = None
    vcard: Optional[str] = None
    resume_url: Optional[str] = None
    resume_download: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    skills: List[str] = strawberry.field(default_factory=list)
    created_at: str
    updated_at: str


@strawberry.type
class WorkExperience:
    id: str
    company: str
    position: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: bool = False
    company_url: Optional[str] = None


@strawberry.type
class Project:
    id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: List[str] = strawberry.field(default_factory=list)


@strawberry.type
class ContactMessage:
    id: str
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    is_read: bool = False
    created_at: str


@strawberry.input
class WorkExperienceInput:
    company: str
    position: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: bool = False
    company_url: Optional[str] = None
    sort_order: int = 0


@strawberry.input
class ProjectInput:
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: List[str] = strawberry.field(default_factory=list)
    sort_order: int = 0


@strawberry.input
class ContactMessageInput:
    name: str
    email: str
    subject: Optional[str] = None
    message: str


@strawberry.input
class PortfolioUpdateInput:
    name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    tagline: Optional[str] = None
    profile_image: Optional[str] = None


def _convert_portfolio_data(data: Dict[str, Any]) -> Portfolio:
    """Convert database portfolio data to GraphQL Portfolio type"""
    if not data:
        return None
    
    # Parse skills JSON if it's a string
    skills = data.get('skills', [])
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except (json.JSONDecodeError, TypeError):
            skills = []
    elif skills is None:
        skills = []
    
    return Portfolio(
        id=data['id'],
        name=data['name'],
        title=data['title'],
        bio=data['bio'],
        tagline=data.get('tagline'),
        profile_image=data.get('profile_image'),
        email=data['email'],
        phone=data.get('phone'),
        vcard=data.get('vcard'),
        resume_url=data.get('resume_url'),
        resume_download=data.get('resume_download'),
        github=data.get('github'),
        twitter=data.get('twitter'),
        skills=skills,
        created_at=data['created_at'],
        updated_at=data['updated_at']
    )


def _convert_work_experience(data: Dict[str, Any]) -> WorkExperience:
    """Convert database work experience to GraphQL type"""
    return WorkExperience(
        id=str(data['id']),
        company=data['company'],
        position=data['position'],
        location=data.get('location'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        description=data.get('description'),
        is_current=data.get('is_current', False),
        company_url=data.get('company_url')
    )


def _convert_project(data: Dict[str, Any]) -> Project:
    """Convert database project to GraphQL type"""
    # Parse technologies JSON if it's a string
    technologies = data.get('technologies', [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    elif technologies is None:
        technologies = []
    
    return Project(
        id=str(data['id']),
        title=data['title'],
        description=data.get('description'),
        url=data.get('url'),
        image_url=data.get('image_url'),
        technologies=technologies
    )


def _convert_message(data: Dict[str, Any]) -> ContactMessage:
    """Convert database message to GraphQL type"""
    return ContactMessage(
        id=str(data['id']),
        name=data['name'],
        email=data['email'],
        subject=data.get('subject'),
        message=data['message'],
        is_read=data.get('is_read', False),
        created_at=data['created_at'].isoformat() if isinstance(data['created_at'], datetime) else str(data['created_at'])
    )


@strawberry.type
class Query:
    @strawberry.field
    async def portfolio(self, portfolio_id: str = "daniel-blackburn") -> Optional[Portfolio]:
        """Get portfolio information"""
        data = await PortfolioDatabase.get_portfolio(portfolio_id)
        return _convert_portfolio_data(data) if data else None
    
    @strawberry.field
    async def work_experience(self, portfolio_id: str = "daniel-blackburn") -> List[WorkExperience]:
        """Get work experience for a portfolio"""
        portfolio_data = await PortfolioDatabase.get_portfolio(portfolio_id)
        if not portfolio_data or 'work_experience' not in portfolio_data:
            return []
        
        return [_convert_work_experience(work) for work in portfolio_data['work_experience']]
    
    @strawberry.field
    async def projects(self, portfolio_id: str = "daniel-blackburn") -> List[Project]:
        """Get projects for a portfolio"""
        portfolio_data = await PortfolioDatabase.get_portfolio(portfolio_id)
        if not portfolio_data or 'projects' not in portfolio_data:
            return []
        
        return [_convert_project(project) for project in portfolio_data['projects']]
    
    @strawberry.field
    async def messages(self, portfolio_id: str = "daniel-blackburn") -> List[ContactMessage]:
        """Get contact messages for a portfolio"""
        data = await PortfolioDatabase.get_messages(portfolio_id)
        return [_convert_message(msg) for msg in data]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def update_portfolio(self, portfolio_id: str, updates: PortfolioUpdateInput) -> Optional[Portfolio]:
        """Update portfolio information"""
        update_dict = {}
        if updates.name is not None:
            update_dict['name'] = updates.name
        if updates.title is not None:
            update_dict['title'] = updates.title
        if updates.bio is not None:
            update_dict['bio'] = updates.bio
        if updates.tagline is not None:
            update_dict['tagline'] = updates.tagline
        if updates.profile_image is not None:
            update_dict['profile_image'] = updates.profile_image
        
        if not update_dict:
            # No updates provided, return current portfolio
            data = await PortfolioDatabase.get_portfolio(portfolio_id)
            return _convert_portfolio_data(data) if data else None
        
        data = await PortfolioDatabase.update_portfolio(portfolio_id, update_dict)
        return _convert_portfolio_data(data) if data else None
    
    @strawberry.mutation
    async def add_work_experience(self, portfolio_id: str, work_data: WorkExperienceInput) -> Optional[WorkExperience]:
        """Add new work experience"""
        work_dict = {
            'company': work_data.company,
            'position': work_data.position,
            'location': work_data.location,
            'start_date': work_data.start_date,
            'end_date': work_data.end_date,
            'description': work_data.description,
            'is_current': work_data.is_current,
            'company_url': work_data.company_url,
            'sort_order': work_data.sort_order
        }
        
        data = await PortfolioDatabase.add_work_experience(portfolio_id, work_dict)
        return _convert_work_experience(data) if data else None
    
    @strawberry.mutation
    async def add_project(self, portfolio_id: str, project_data: ProjectInput) -> Optional[Project]:
        """Add new project"""
        project_dict = {
            'title': project_data.title,
            'description': project_data.description,
            'url': project_data.url,
            'image_url': project_data.image_url,
            'technologies': project_data.technologies,
            'sort_order': project_data.sort_order
        }
        
        data = await PortfolioDatabase.add_project(portfolio_id, project_dict)
        return _convert_project(data) if data else None
    
    @strawberry.mutation
    async def save_contact_message(self, portfolio_id: str, message_data: ContactMessageInput) -> Optional[ContactMessage]:
        """Save a contact message"""
        message_dict = {
            'name': message_data.name,
            'email': message_data.email,
            'subject': message_data.subject,
            'message': message_data.message
        }
        
        data = await PortfolioDatabase.save_message(portfolio_id, message_dict)
        return _convert_message(data) if data else None


# Create the GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)