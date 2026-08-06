import os
import sys
import django
import random
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facutrack.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from facutrack_app.models import (
    UserProfile, Department, Questionnaire, Evaluation,
    EvaluationAnswer, DraftEvaluation, ActivityLog,
    VisitorLog, RecentActivity, LoginAttempt, UserRole, Gender
)

User = get_user_model()


def clear_database():
    print("Clearing existing data...")
    LoginAttempt.objects.all().delete()
    RecentActivity.objects.all().delete()
    VisitorLog.objects.all().delete()
    ActivityLog.objects.all().delete()
    DraftEvaluation.objects.all().delete()
    EvaluationAnswer.objects.all().delete()
    Evaluation.objects.all().delete()
    Questionnaire.objects.all().delete()
    UserProfile.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    Department.objects.all().delete()
    print("Database cleared.")


def create_departments():
    print("Creating grade levels...")
    departments_data = [
        "G-7",
        "G-8",
        "G-9",
        "G-10",
        "G-11",
        "G-12",
    ]
    departments = []
    for name in departments_data:
        dept, created = Department.objects.get_or_create(department_name=name)
        departments.append(dept)
        if created:
            print(f"  Created grade level: {name}")
    return departments


def create_questionnaires():
    print("Creating questionnaires...")
    questions_data = [
        "How satisfied are you with the instructor's knowledge of the subject matter?",
        "How well does the instructor explain complex concepts?",
        "How effectively does the instructor use class time?",
        "How responsive is the instructor to student questions?",
        "How fair and clear are the grading criteria?",
        "How well does the instructor provide feedback on assignments?",
        "How organized is the course structure?",
        "How relevant are the course materials to the learning objectives?",
        "How effectively does the instructor use technology in teaching?",
        "How approachable is the instructor during office hours?",
        "How well does the instructor encourage class participation?",
        "How satisfied are you with the overall learning experience?",
        "How well does the instructor relate theory to practical applications?",
        "How effectively does the instructor manage classroom behavior?",
        "How well does the instructor accommodate different learning styles?",
        "How clear are the course expectations and requirements?",
        "How timely is the instructor in returning graded work?",
        "How well does the instructor foster a positive learning environment?",
        "How effectively does the instructor use visual aids and demonstrations?",
        "How satisfied are you with the instructor's availability for consultation?",
    ]
    questionnaires = []
    for q_text in questions_data:
        q, created = Questionnaire.objects.get_or_create(question=q_text)
        questionnaires.append(q)
        if created:
            print(f"  Created question: {q_text[:50]}...")
    return questionnaires


def create_admin_user():
    print("Creating admin user...")
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@facutrack.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_active': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        UserProfile.objects.create(
            user=admin_user,
            full_name='Admin User',
            role=UserRole.ADMIN,
            gender=Gender.MALE,
            temp_password='admin123',
        )
        print("  Created admin user: admin / admin123")
    return admin_user


def create_staff_users(departments):
    print("Creating staff users...")
    staff_data = [
        {
            'username': 'prof.reyes',
            'email': 'reyes@facutrack.com',
            'first_name': 'Antonio',
            'last_name': 'Reyes',
            'full_name': 'Prof. Antonio Reyes',
            'gender': Gender.MALE,
            'dept_index': 0,  # G-7
        },
        {
            'username': 'prof.santos',
            'email': 'santos@facutrack.com',
            'first_name': 'Maria',
            'last_name': 'Santos',
            'full_name': 'Prof. Maria Santos',
            'gender': Gender.FEMALE,
            'dept_index': 0,  # G-7
        },
        {
            'username': 'prof.cruz',
            'email': 'cruz@facutrack.com',
            'first_name': 'Juan',
            'last_name': 'Cruz',
            'full_name': 'Prof. Juan Cruz',
            'gender': Gender.MALE,
            'dept_index': 1,  # G-8
        },
        {
            'username': 'prof.garcia',
            'email': 'garcia@facutrack.com',
            'first_name': 'Ana',
            'last_name': 'Garcia',
            'full_name': 'Prof. Ana Garcia',
            'gender': Gender.FEMALE,
            'dept_index': 1,  # G-8
        },
        {
            'username': 'prof.mendoza',
            'email': 'mendoza@facutrack.com',
            'first_name': 'Carlos',
            'last_name': 'Mendoza',
            'full_name': 'Prof. Carlos Mendoza',
            'gender': Gender.MALE,
            'dept_index': 2,  # G-9
        },
        {
            'username': 'prof.lopez',
            'email': 'lopez@facutrack.com',
            'first_name': 'Sofia',
            'last_name': 'Lopez',
            'full_name': 'Prof. Sofia Lopez',
            'gender': Gender.FEMALE,
            'dept_index': 2,  # G-9
        },
        {
            'username': 'prof.rivera',
            'email': 'rivera@facutrack.com',
            'first_name': 'Miguel',
            'last_name': 'Rivera',
            'full_name': 'Prof. Miguel Rivera',
            'gender': Gender.MALE,
            'dept_index': 3,  # G-10
        },
        {
            'username': 'prof.torres',
            'email': 'torres@facutrack.com',
            'first_name': 'Isabella',
            'last_name': 'Torres',
            'full_name': 'Prof. Isabella Torres',
            'gender': Gender.FEMALE,
            'dept_index': 3,  # G-10
        },
        {
            'username': 'prof.flores',
            'email': 'flores@facutrack.com',
            'first_name': 'Diego',
            'last_name': 'Flores',
            'full_name': 'Prof. Diego Flores',
            'gender': Gender.MALE,
            'dept_index': 4,  # G-11
        },
        {
            'username': 'prof.gonzales',
            'email': 'gonzales@facutrack.com',
            'first_name': 'Camila',
            'last_name': 'Gonzales',
            'full_name': 'Prof. Camila Gonzales',
            'gender': Gender.FEMALE,
            'dept_index': 4,  # G-11
        },
        {
            'username': 'prof.hernandez',
            'email': 'hernandez@facutrack.com',
            'first_name': 'Rafael',
            'last_name': 'Hernandez',
            'full_name': 'Prof. Rafael Hernandez',
            'gender': Gender.MALE,
            'dept_index': 5,  # G-12
        },
        {
            'username': 'prof.diaz',
            'email': 'diaz@facutrack.com',
            'first_name': 'Valentina',
            'last_name': 'Diaz',
            'full_name': 'Prof. Valentina Diaz',
            'gender': Gender.FEMALE,
            'dept_index': 5,  # G-12
        },
    ]

    users = []
    for data in staff_data:
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'is_active': True,
            }
        )
        if created:
            password = 'staff123'
            user.set_password(password)
            user.save()
            UserProfile.objects.create(
                user=user,
                full_name=data['full_name'],
                role=UserRole.STAFF,
                gender=data['gender'],
                department=departments[data['dept_index']],
                temp_password=password,
            )
            print(f"  Created staff: {data['username']} / {password}")
        users.append(user)
    return users


def create_evaluations(users, departments, questionnaires):
    print("Creating evaluations...")
    evaluator_emails = [
        'student1@school.edu',
        'student2@school.edu',
        'student3@school.edu',
        'student4@school.edu',
        'student5@school.edu',
        'student6@school.edu',
        'student7@school.edu',
        'student8@school.edu',
        'student9@school.edu',
        'student10@school.edu',
        'john.doe@school.edu',
        'jane.smith@school.edu',
        'bob.wilson@school.edu',
        'alice.johnson@school.edu',
        'charlie.brown@school.edu',
    ]

    evaluator_names = [
        'John Doe',
        'Jane Smith',
        'Bob Wilson',
        'Alice Johnson',
        'Charlie Brown',
        'Diana Prince',
        'Edward Norton',
        'Fiona Apple',
        'George Lucas',
        'Helen Mirren',
        'Ivan Drago',
        'Julia Roberts',
        'Kevin Hart',
        'Laura Palmer',
        'Michael Scott',
    ]

    sections = ['Diamond', 'Gold', 'Silver', 'Pearl', 'Ruby', 'Sapphire']

    sample_comments = [
        "Great teaching style, very engaging lectures.",
        "Would appreciate more hands-on activities.",
        "Explains lessons clearly and is very patient.",
        "Sometimes talks too fast, hard to follow.",
        "Very approachable and helpful during consultations.",
        "Needs to improve time management in class.",
        "Makes the subject interesting and fun to learn.",
        "Could provide more real-world examples.",
        "Always well-prepared for every lesson.",
        "Fair and transparent grading system.",
        "Encourages students to ask questions.",
        "Assignments are relevant and helpful for learning.",
        "Very supportive and motivates students to do better.",
        "Would like more visual aids during discussions.",
        "Respectful and creates a safe learning environment.",
    ]

    now = timezone.now()
    evaluations = []

    for i in range(50):
        faculty = random.choice(users)
        profile = faculty.profile
        department = profile.department if profile else random.choice(departments)

        days_ago = random.randint(0, 180)
        created_at = now - timedelta(days=days_ago)

        grade_num = department.department_name.replace("G-", "")
        section = random.choice(sections)
        course_section = f"G{grade_num}-{section}"

        comment = random.choice(sample_comments) if random.random() > 0.5 else ""

        evaluation = Evaluation.objects.create(
            email=random.choice(evaluator_emails),
            full_name=random.choice(evaluator_names) if random.random() > 0.3 else '',
            department=department,
            course_section=course_section,
            faculty=faculty,
            comments=comment,
            created_at=created_at,
        )

        for questionnaire in questionnaires:
            rating_weights = [0.05, 0.10, 0.25, 0.35, 0.25]  # 1,2,3,4,5
            rating = random.choices([1, 2, 3, 4, 5], weights=rating_weights)[0]

            EvaluationAnswer.objects.create(
                evaluation=evaluation,
                questionnaire=questionnaire,
                rating=rating,
            )

        evaluations.append(evaluation)

        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1} evaluations...")

    print(f"  Created {len(evaluations)} evaluations with answers.")
    return evaluations


def create_draft_evaluations():
    print("Creating draft evaluations...")
    drafts_data = [
        {
            'email': 'draft1@school.edu',
            'saved_progress': {'q_1': '3', 'q_2': '4', 'q_3': '5'},
        },
        {
            'email': 'draft2@school.edu',
            'saved_progress': {'q_1': '2', 'q_2': '3'},
        },
        {
            'email': 'draft3@school.edu',
            'saved_progress': {'q_1': '4', 'q_2': '4', 'q_3': '4', 'q_4': '5'},
        },
    ]

    for data in drafts_data:
        DraftEvaluation.objects.get_or_create(
            email=data['email'],
            defaults={'saved_progress': data['saved_progress']}
        )
    print(f"  Created {len(drafts_data)} draft evaluations.")


def create_activity_logs(users):
    print("Creating activity logs...")
    now = timezone.now()
    endpoints = [
        '/login/',
        '/admin/dashboard/',
        '/admin/users/',
        '/admin/departments/',
        '/admin/questionnaire/',
        '/admin/rankings/',
        '/admin/reports/',
        '/admin/logs/',
        '/admin/analytics/',
        '/faculty/dashboard/',
        '/faculty/feedback/',
        '/faculty/settings/',
        '/rate/',
    ]

    ips = [
        '192.168.1.100',
        '192.168.1.101',
        '192.168.1.102',
        '10.0.0.50',
        '10.0.0.51',
        '172.16.0.10',
        '172.16.0.11',
    ]

    for i in range(100):
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        ActivityLog.objects.create(
            ip_address=random.choice(ips),
            user=random.choice(users) if random.random() > 0.3 else None,
            method=random.choice(['GET', 'POST']),
            endpoint=random.choice(endpoints),
            response_status=random.choice([200, 200, 200, 200, 301, 302, 400, 404]),
            timestamp=timestamp,
        )
    print("  Created 100 activity logs.")


def create_visitor_logs():
    print("Creating visitor logs...")
    now = timezone.now()
    pages = [
        '/',
        '/rate/',
        '/login/',
        '/about',
        '/features',
        '/contact',
    ]

    ips = [
        '192.168.1.100',
        '192.168.1.101',
        '192.168.1.102',
        '10.0.0.50',
        '10.0.0.51',
        '172.16.0.10',
        '172.16.0.11',
        '203.0.113.50',
        '198.51.100.25',
    ]

    for i in range(200):
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        VisitorLog.objects.create(
            ip_address=random.choice(ips),
            visited_page=random.choice(pages),
            timestamp=timestamp,
        )
    print("  Created 200 visitor logs.")


def create_recent_activities(users):
    print("Creating recent activities...")
    now = timezone.now()
    activities = [
        "User 'admin' signed in.",
        "User 'prof.reyes' signed in.",
        "User 'prof.santos' signed in.",
        "New evaluation submitted for prof.reyes.",
        "New evaluation submitted for prof.santos.",
        "New evaluation submitted for prof.cruz.",
        "Grade level 'G-7' updated.",
        "User 'prof.garcia' created.",
        "Questionnaire added: 'How satisfied are you...'",
        "Report generated: Faculty Ranking (PDF).",
        "System logs cleared.",
        "SMTP test email sent to admin@facutrack.com.",
        "User 'prof.mendoza' updated.",
        "Grade level 'G-9' created.",
        "Credentials emailed to prof.lopez@facutrack.com.",
    ]

    for i, activity_text in enumerate(activities):
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago)

        RecentActivity.objects.create(
            activity=activity_text,
            user=random.choice(users) if random.random() > 0.5 else None,
            timestamp=timestamp,
        )
    print(f"  Created {len(activities)} recent activities.")


def create_login_attempts():
    print("Creating login attempts...")
    now = timezone.now()
    usernames = ['admin', 'prof.reyes', 'prof.santos', 'unknown_user', 'hacker']
    ips = ['192.168.1.100', '10.0.0.50', '203.0.113.50']

    for i in range(15):
        hours_ago = random.randint(0, 48)
        timestamp = now - timedelta(hours=hours_ago)

        LoginAttempt.objects.create(
            username=random.choice(usernames),
            ip_address=random.choice(ips),
            timestamp=timestamp,
        )
    print("  Created 15 login attempts.")


def create_superuser():
    print("Checking for superuser...")
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@facutrack.com',
            password='superadmin123',
        )
        print("  Created superuser: superadmin / superadmin123")
    else:
        print("  Superuser already exists.")


def main():
    print("=" * 60)
    print("FacuTrack Database Seed Script")
    print("=" * 60)
    print()

    response = input("This will clear existing data and create new sample data. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Seed cancelled.")
        return

    print()
    clear_database()
    print()

    departments = create_departments()
    print()

    questionnaires = create_questionnaires()
    print()

    admin = create_admin_user()
    print()

    staff_users = create_staff_users(departments)
    all_users = [admin] + staff_users
    print()

    create_superuser()
    print()

    evaluations = create_evaluations(staff_users, departments, questionnaires)
    print()

    create_draft_evaluations()
    print()

    create_activity_logs(all_users)
    print()

    create_visitor_logs()
    print()

    create_recent_activities(all_users)
    print()

    create_login_attempts()
    print()

    # Summary
    print("=" * 60)
    print("Seed Complete!")
    print("=" * 60)
    print()
    print("Sample Accounts:")
    print("  Admin:      admin / admin123")
    print("  Superuser:  superadmin / superadmin123")
    print("  Staff:      prof.reyes / staff123")
    print("              prof.santos / staff123")
    print("              prof.cruz / staff123")
    print("              ... (12 staff accounts total)")
    print()
    print("Database Statistics:")
    print(f"  Grade Levels:       {Department.objects.count()}")
    print(f"  Questionnaires:     {Questionnaire.objects.count()}")
    print(f"  Users:              {User.objects.count()}")
    print(f"  User Profiles:      {UserProfile.objects.count()}")
    print(f"  Evaluations:        {Evaluation.objects.count()}")
    print(f"  Evaluation Answers: {EvaluationAnswer.objects.count()}")
    print(f"  Draft Evaluations:  {DraftEvaluation.objects.count()}")
    print(f"  Activity Logs:      {ActivityLog.objects.count()}")
    print(f"  Visitor Logs:       {VisitorLog.objects.count()}")
    print(f"  Recent Activities:  {RecentActivity.objects.count()}")
    print(f"  Login Attempts:     {LoginAttempt.objects.count()}")
    print()
    print("You can now run the server: python manage.py runserver")


if __name__ == '__main__':
    main()
