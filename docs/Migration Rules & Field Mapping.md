Migration Rules & Field Mapping

1. No Duplicate Tasks - Prioritize Client Projects

When a task exists in multiple Asana projects, do not duplicate it. Choose the client project over the individual team member project. If you're unsure which is which, prioritize the project that appears to be client-facing."

The Problem:

Some tasks in Asana exist in multiple projects (e.g., a task might be in both "Brandywine" client project AND "Lena's" individual project)
During migration, these could be duplicated in Scoro if not handled properly

The Solution:

DO NOT duplicate tasks if they appear in multiple Asana projects
Prioritize CLIENT projects over TEAM MEMBER projects
If a task is in both a client project (e.g., "Brandywine") and an individual's project (e.g., "Lena's project"), assign it to the CLIENT project ("Brandywine")

Example:
Task: "Review Facebook Ads performance"
Appears in:
  - Brandywine project (CLIENT)
  - Lena's project (TEAM MEMBER)
Action: Assign to "Brandywine" project only


2. Client-First Association
Each project in Scoro needs to be associated with a client/company record. Ensure your migration script creates or references these client records and links projects to them.

The Requirement:
- In Scoro, clients are “company” and “contacts” records (not portfolios like in Asana)
- Projects must be linked to these client/company records
- This is different from how Asana organizes projects


3. Project Overview → Project Info/Details
Map the Asana overview field to the appropriate Scoro description field based on whether it's task-level or project-level content."

The Mapping:
Asana “Project Overview” content should map to Scoro project description/details field
At task level: Overview goes to "Description" field
At project level: There's a separate field for project-level overview

Category Mapping - If Blank, Use "Other"
If a task in Asana has no category assigned, map it to 'Other' in Scoro. Do not attempt to infer the category based on who the task is assigned to.

The Rule:

If a task has no category assigned in Asana, map it to "Other" in Scoro
DO NOT try to auto-assign based on assignee
❌ Don't assume "Lina = Facebook Ads"
❌ Don't assume "Elizabeth = Facebook Ads"
✅ If blank → "Other"

Rationale:
Users need to manually verify and choose the correct category during transition
Auto-assignment might be 90% accurate, but users will get used to it being automatic and won't fix the 10% that's wrong
Better to force manual selection during the transition period


4. Updated Activity Types (Service Categories)
Activity Types in Scoro are being updated to match the service list. 
Critical Changes:
- Time Task Tracking Field → DELETE

The "Time Task Tracking" custom field is being eliminated completely
Only use the Activity Types dropdown (the main service category field on the left)
This is the field that currently shows options like "blogs"

- Key Mapping Rules:
Existing categories in Asana will need to change to follow this conversation before the Scoro import. 


- Map to the following Activities in Scoro (already created)
Asana Categories -> Scoro
Account Management -> Project Management
Blogs -> SEO
Brand Package -> Branding
Brochure -> Brochure
Client Management -> Project Management
Content & Creative -> Graphic Design Support
Contractor/Homeowner Brochure -> Brochure
Copywriter -> Website - New 
CrewRecruiter -> CrewRecruiter
Dealer Brochure -> Brochure
Design - New Website -> Website - New 
Email -> Email
Facebook Ads -> Facebook Ads
Google Ads -> Google Ads
Halstead -> Halstead Marketing
Internal Operations -> Administrative - Internal
Lead Magnet -> Lead Magnet
LinkedIn Ads -> Linkedin Ads
Marketing Collateral Package -> Branding
Meetings -> Project Management
Microsoft Ads -> Microsoft Ads
Offboarding, Pausing, & Ending Projects -> Project Management
OKRs -> Administrative - Internal
Onboarding -> Onboarding
Onboarding | Access -> Onboarding
Onboarding | After Client Kick Off Call -> Onboarding
Onboarding | Before Client Kick Off Call -> Onboarding
Onboarding | During Client Kick Off Call -> Onboarding
Onboarding | Lead Tracking & Review Building -> Onboarding
Other -> Other
Paid Advertising -> Google Ads
PM Status Update -> Project Management
SEO -> SEO
SEO Services -> SEO
Social Media -> Social Posting
Social Posting -> Social Posting
Special Projects -> Other
Videography -> Videography
Website - One Week Before Go Live -> Website - New 
Website Core Pages -> Website - New 
Website Design -> Website - New 
Website Development -> Website - New 
Website Final Approval -> Website - New 
Website Full Build -> Website - New 
Website Go Live -> Website - New 
Website Homepage in Squarespace -> Website - New 
Website Homepage Mockup -> Website - New 
Website Strategy -> Website - New 
Website Updates -> Website - SEO