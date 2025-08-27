#!/usr/bin/env python3
"""
GraphQL Demo - Demonstrates the GraphQL API functionality
"""
import asyncio
import json
from datetime import datetime

def demo_graphql_queries():
    """Show example GraphQL queries for the portfolio API"""
    
    print("=== GraphQL Portfolio API Demo ===\n")
    
    print("🚀 Your GraphQL FastAPI application is now ready!")
    print("\n📍 Endpoints:")
    print("   • GraphQL API: http://localhost:8000/graphql")
    print("   • GraphQL Playground: http://localhost:8000/playground")
    print("   • Health Check: http://localhost:8000/health")
    print("   • Portfolio Website: http://localhost:8000/")
    
    print("\n📋 Sample GraphQL Queries:\n")
    
    # Query Examples
    print("1️⃣ Get Portfolio Information:")
    portfolio_query = """
    query GetPortfolio {
      portfolio(portfolioId: "daniel-blackburn") {
        id
        name
        title
        bio
        email
        skills
        github
        twitter
      }
    }
    """
    print(portfolio_query)
    
    print("\n2️⃣ Get Work Experience:")
    work_query = """
    query GetWorkExperience {
      workExperience(portfolioId: "daniel-blackburn") {
        id
        company
        position
        location
        startDate
        endDate
        isCurrent
        description
      }
    }
    """
    print(work_query)
    
    print("\n3️⃣ Get Projects:")
    projects_query = """
    query GetProjects {
      projects(portfolioId: "daniel-blackburn") {
        id
        title
        description
        url
        technologies
      }
    }
    """
    print(projects_query)
    
    # Mutation Examples
    print("\n🔄 Sample GraphQL Mutations:\n")
    
    print("4️⃣ Update Portfolio:")
    update_mutation = """
    mutation UpdatePortfolio {
      updatePortfolio(
        portfolioId: "daniel-blackburn",
        updates: {
          title: "Senior Software Engineer",
          tagline: "Building the future with code"
        }
      ) {
        id
        name
        title
        tagline
      }
    }
    """
    print(update_mutation)
    
    print("\n5️⃣ Add Work Experience:")
    add_work_mutation = """
    mutation AddWorkExperience {
      addWorkExperience(
        portfolioId: "daniel-blackburn",
        workData: {
          company: "Tech Innovators Inc",
          position: "Senior Developer",
          location: "Remote",
          startDate: "2024",
          isCurrent: true,
          description: "Leading development of cutting-edge applications"
        }
      ) {
        id
        company
        position
        isCurrent
      }
    }
    """
    print(add_work_mutation)
    
    print("\n6️⃣ Add Project:")
    add_project_mutation = """
    mutation AddProject {
      addProject(
        portfolioId: "daniel-blackburn",
        projectData: {
          title: "GraphQL Portfolio API",
          description: "Modern portfolio backend with GraphQL and FastAPI",
          url: "https://github.com/blackburnd/cloud_machine_repo",
          technologies: ["Python", "FastAPI", "GraphQL", "PostgreSQL"]
        }
      ) {
        id
        title
        description
        technologies
      }
    }
    """
    print(add_project_mutation)
    
    print("\n7️⃣ Save Contact Message:")
    contact_mutation = """
    mutation SaveContactMessage {
      saveContactMessage(
        portfolioId: "daniel-blackburn",
        messageData: {
          name: "John Doe",
          email: "john@example.com",
          subject: "Collaboration Opportunity",
          message: "Hi! I'd love to discuss a potential project collaboration."
        }
      ) {
        id
        name
        email
        subject
        createdAt
      }
    }
    """
    print(contact_mutation)
    
    print("\n💡 How to Test:")
    print("1. Start your application: python3 main.py")
    print("2. Open GraphQL Playground: http://localhost:8000/playground")
    print("3. Copy and paste the queries above")
    print("4. Click the ▶️ button to execute")
    
    print("\n🔧 Troubleshooting:")
    print("• If database connection fails, check your PostgreSQL server")
    print("• Run: python3 test_database.py to test DB connection")
    print("• Run: python3 test_graphql.py to test GraphQL functionality")
    
    print("\n📊 Database Schema:")
    print("• portfolios - Main portfolio information")
    print("• work_experience - Job history and experience")  
    print("• projects - Portfolio projects and work samples")
    print("• contact_messages - Messages from website visitors")
    
    print("\n🌟 Features Implemented:")
    print("✅ Complete GraphQL schema with queries and mutations")
    print("✅ PostgreSQL database integration")
    print("✅ FastAPI with modern lifespan management")
    print("✅ Comprehensive error handling")
    print("✅ CI/CD pipeline with Google Cloud Build")
    print("✅ GraphQL Playground for testing")
    print("✅ Portfolio website serving")
    print("✅ Health check endpoints")
    
    print(f"\n🎉 GraphQL FastAPI Portfolio API is ready to use!")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    demo_graphql_queries()