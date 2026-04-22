# E-HealthShield
1. ONE-TIME SETUP (for eachone)
 git clone https://github.com/syedabdulla0710/E-HealthShield.git
 cd E-HealthShield

2.Each member should ONLY use their branch:
Frontend person:
   git checkout frontend-setup
Backend person:
   git checkout backend-setup
Blockchain person:
   git checkout blockchain-setup
Crypto person:
   git checkout crypto-setup

3.Before starting work (ALWAYS DO THIS)
  git checkout your-branch-name
  git pull origin your-branch-name

4.After coding (SAVE YOUR WORK)
  git add .
  git commit -m "your message"
  git push origin your-branch-name

5.MERGING TO MAIN 

👉 Do this only after work is ready
Step 1: Go to GitHub
Click Pull Requests
Click New Pull Request
Step 2:
base → main
compare → frontend-setup (or any branch)
Step 3:
Click Create Pull Request
Click Merge Pull Request

6.AFTER MERGE (VERY IMPORTANT)
Everyone must update their code:
   git checkout main
   git pull origin main

TEAM RULES (DON’T BREAK THESE)
❌ NEVER:
   git push origin main

SIMPLE FLOW (REMEMBER THIS)
Pull → Code → Add → Commit → Push → PR → Merge
