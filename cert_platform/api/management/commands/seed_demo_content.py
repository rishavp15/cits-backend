from django.core.management.base import BaseCommand

from api.models import Assessment, AssessmentQuestion, Course


QUESTIONS = [
    {
        "prompt": "Which library is primarily used for data manipulation in Python?",
        "options": ["Pandas", "React", "Vue", "Laravel"],
        "answer": "Pandas",
    },
    {
        "prompt": "What does CSV stand for?",
        "options": [
            "Computer Style View",
            "Comma Separated Values",
            "Code Syntax Variable",
            "None",
        ],
        "answer": "Comma Separated Values",
    },
    {
        "prompt": "Which metric is commonly used to evaluate a classification model?",
        "options": ["Mean Squared Error", "R-Squared", "Accuracy", "Variance"],
        "answer": "Accuracy",
    },
    {
        "prompt": "What is the purpose of the 'head()' function in Pandas?",
        "options": [
            "Delete the first row",
            "Return the last 5 rows",
            "Return the first n rows",
            "Calculate the mean",
        ],
        "answer": "Return the first n rows",
    },
    {
        "prompt": "Which of the following is a supervised learning algorithm?",
        "options": [
            "K-Means Clustering",
            "Linear Regression",
            "Apriori",
            "DBSCAN",
        ],
        "answer": "Linear Regression",
    },
]


COURSES = [
    {
        "slug": "data-science",
        "title": "Data Science & AI",
        "description": "Statistics, Python, Deep Learning, and Industrial Analytics.",
        "hero_tagline": "Data Science & AI · Evaluate first, then certify",
        "hero_title": "Master the Data Science Fast-Track Curriculum",
        "hero_description": "Take the competency evaluation covering Python, analytics, and AI foundations. Submit your industrial project, unlock mentor review, and receive globally trusted credentials.",
        "subject": "Data Science & AI",
        "icon": "brain",
        "color": "bg-indigo-500",
        "students": 12000,
        "duration_hours": 180,
        "logo_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429",
        "hero_image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
        "card_image_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429",
        "gallery_images": [
            "https://images.unsplash.com/photo-1483478550801-ceba5fe50e8e",
            "https://images.unsplash.com/photo-1517430816045-df4b7de11d1d",
        ],
        "syllabus": [
            {
                "title": "Month 1 · Fundamentals",
                "topics": ["Python foundations", "Statistics refresher", "Git for analysts"],
            },
            {
                "title": "Month 2 · Analysis",
                "topics": ["EDA with pandas", "PowerBI dashboards", "SQL modelling"],
            },
            {
                "title": "Month 3 · AI Delivery",
                "topics": ["TensorFlow models", "MLOps basics", "Stakeholder reporting"],
            },
        ],
        "class_links": [
            {"label": "Self-paced playlist", "url": "https://youtube.com/@iscb"},
            {"label": "Dataset repository", "url": "https://github.com/iscb/datasets"},
        ],
        "competencies": [
            {
                "title": "Python & Stats",
                "description": "Covers numpy, pandas, vectorized maths, and probability.",
                "weight": "35%",
            },
            {
                "title": "Analytics Automation",
                "description": "SQL joins, BI dashboards, Excel power tools.",
                "weight": "25%",
            },
            {
                "title": "AI Foundations",
                "description": "TensorFlow, model tuning, deployment readiness.",
                "weight": "40%",
            },
        ],
        "plan_highlights": {
            "industrial": {
                "summary": "3-month industrial sprint with mentor-reviewed project.",
                "focus": ["Project verification", "180-hour record", "Internship recommendation"],
            },
            "master": {
                "summary": "Master certification, deeper research deliverables, leadership rubric.",
                "focus": ["Capstone defense", "Leadership report", "Mentor hours"],
            },
        },
        "playlist_modules": [
            {
                "title": "Python & Statistics Bootup",
                "description": "Quick refresher on Python syntax, numpy, and probability.",
                "videos": [
                    {
                        "title": "Python foundations in 45 minutes",
                        "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
                        "duration": "45m",
                    },
                    {
                        "title": "Statistics for Data Science",
                        "url": "https://www.youtube.com/watch?v=xxpc-HPKN28",
                        "duration": "32m",
                    },
                ],
            },
            {
                "title": "Analytics Automation",
                "description": "Dashboards, SQL modelling, and storytelling.",
                "videos": [
                    {
                        "title": "PowerBI crash course",
                        "url": "https://www.youtube.com/watch?v=agdi8G8fqIk",
                        "duration": "28m",
                    },
                    {
                        "title": "SQL joins deep dive",
                        "url": "https://www.youtube.com/watch?v=9Pzj7Aj25lw",
                        "duration": "26m",
                    },
                ],
            },
        ],
        "certificate_types": ["basic", "industrial", "master"],
        "open_standards_label": "Data Science Open Standards",
        "trust_grid": [
            {
                "title": "CS Fundamentals",
                "description": "Structure adapted from Harvard University CS50 OpenCourseWare.",
                "icon": "terminal",
            },
            {
                "title": "Advanced Excel",
                "description": "Data modeling protocols based on Microsoft professional standards.",
                "icon": "table",
            },
            {
                "title": "Deep Learning",
                "description": "Neural network implementation using Google's TensorFlow framework.",
                "icon": "brain-circuit",
            },
            {
                "title": "Visual Analytics",
                "description": "Dashboarding aligned with Tableau & Salesforce BI methodologies.",
                "icon": "pie-chart",
            },
        ],
        "certifications": [
            {
                "label": "Skill Validation",
                "tier": "Accelerator",
                "price": "₹499",
                "original_price": "₹799",
                "description": "15-min evaluation covering Python, statistics, and analytics reasoning.",
            },
            {
                "label": "Industrial Training",
                "tier": "Fast-Track",
                "price": "₹999",
                "original_price": "₹1,499",
                "description": "Project-backed certification with mentor review and internship letter.",
            },
            {
                "label": "Mastery Diploma",
                "tier": "Executive",
                "price": "₹1,499",
                "original_price": "₹2,199",
                "description": "Six-month portfolio audit with AI research endorsement.",
            },
        ],
        "testimonials": [
            {
                "name": "Sarah Jenkins",
                "role": "Data Analyst @ TechFlow",
                "quote": "Fast-Track mode is a game changer. I skipped the basics I already knew and got verified in 48 hours.",
            }
        ],
        "assessments": [
            {
                "title": "Data Science Core Evaluation",
                "slug": "data-science-core",
                "instructions": "15-min MCQ covering Python, SQL, statistics, and TensorFlow basics.",
            }
        ],
    },
    {
        "slug": "full-stack",
        "title": "Full Stack Engineering",
        "description": "React, Node.js, databases, and cloud pipelines for production apps.",
        "hero_tagline": "Full Stack Engineering · Evaluate first, launch faster",
        "hero_title": "Ship production-ready applications with confidence",
        "hero_description": "Prove mastery across React, Node.js, databases, and cloud pipelines before unlocking certification.",
        "subject": "Full Stack Engineering",
        "icon": "code",
        "color": "bg-teal-500",
        "students": 8500,
        "duration_hours": 200,
        "hero_image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475",
        "card_image_url": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6",
        "gallery_images": [],
        "trust_grid": [],
        "certifications": [],
        "testimonials": [],
        "plan_highlights": {
            "industrial": {
                "summary": "Industrial credential ensures production readiness across the stack.",
                "focus": ["Capstone build", "DevOps review", "Mentor endorsement"],
            },
            "master": {
                "summary": "Master certification adds architecture deep dives and leadership evidence.",
                "focus": ["System design viva", "Resilience playbooks"],
            },
        },
        "playlist_modules": [
            {
                "title": "Frontend Systems",
                "description": "Design systems, hooks, and testing routines.",
                "videos": [
                    {
                        "title": "Advanced React patterns",
                        "url": "https://www.youtube.com/watch?v=0ZJgIjIuY7U",
                        "duration": "35m",
                    }
                ],
            },
            {
                "title": "Cloud Ready Backends",
                "description": "Node.js APIs, databases, and cloud deployments.",
                "videos": [
                    {
                        "title": "Node + Express best practices",
                        "url": "https://www.youtube.com/watch?v=Oe421EPjeBE",
                        "duration": "40m",
                    }
                ],
            },
        ],
        "assessments": [
            {
                "title": "Full Stack Readiness Check",
                "slug": "full-stack-core",
                "instructions": "Covers React patterns, REST APIs, and database modelling.",
            }
        ],
    },
    {
        "slug": "cybersecurity",
        "title": "Cybersecurity Analyst",
        "description": "Network defense, ethical hacking, and security protocols aligned with ISO standards.",
        "hero_tagline": "Cybersecurity Analyst · Evaluate quickly, deploy safely",
        "hero_title": "Protect enterprise workloads with confidence",
        "hero_description": "Demonstrate hands-on mastery of network defense, incident response, and compliance benchmarks.",
        "subject": "Cybersecurity",
        "icon": "shield",
        "color": "bg-rose-500",
        "students": 5000,
        "duration_hours": 160,
        "hero_image_url": "https://images.unsplash.com/photo-1483478550801-ceba5fe50e8e",
        "card_image_url": "https://images.unsplash.com/photo-1457433575995-8407028a9970",
        "gallery_images": [],
        "trust_grid": [],
        "certifications": [],
        "testimonials": [],
        "plan_highlights": {
            "industrial": {
                "summary": "Industrial credential validates SOC-ready skillsets.",
                "focus": ["Threat hunt logs", "Playbook execution"],
            },
            "master": {
                "summary": "Master certification adds red-team/blue-team leadership evaluations.",
                "focus": ["Purple teaming", "Regulatory mappings"],
            },
        },
        "playlist_modules": [
            {
                "title": "Blue Team Ops",
                "description": "Monitoring, SIEM tuning, incident response drills.",
                "videos": [
                    {
                        "title": "SOC foundations",
                        "url": "https://www.youtube.com/watch?v=kCwVnIU0QLA",
                        "duration": "30m",
                    }
                ],
            },
        ],
        "assessments": [
            {
                "title": "Cybersecurity Foundations",
                "slug": "cybersecurity-core",
                "instructions": "Benchmarks ISO-aligned security decision making.",
            }
        ],
    },
]


class Command(BaseCommand):
    help = "Seeds demo courses, assessments, and questions so the frontend has data to display."

    def handle(self, *args, **options):
        created_courses = 0
        created_assessments = 0
        created_questions = 0

        for course_data in COURSES:
            assessments = course_data.pop("assessments", [])
            course, course_created = Course.objects.update_or_create(
                slug=course_data["slug"],
                defaults=course_data,
            )
            if course_created:
                created_courses += 1

            for assessment_data in assessments:
                assessment_questions = assessment_data.pop("questions", QUESTIONS)
                assessment, assessment_created = Assessment.objects.update_or_create(
                    slug=assessment_data["slug"],
                    defaults={
                        **assessment_data,
                        "course": course,
                    },
                )
                if assessment_created:
                    created_assessments += 1

                # Reset questions so the seed command is idempotent
                assessment.questions.all().delete()
                for order, question in enumerate(assessment_questions, start=1):
                    AssessmentQuestion.objects.create(
                        assessment=assessment,
                        prompt=question["prompt"],
                        options=question["options"],
                        answer=question["answer"],
                        order=order,
                    )
                    created_questions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Courses: {created_courses}, Assessments: {created_assessments}, Questions: {created_questions}"
            )
        )

