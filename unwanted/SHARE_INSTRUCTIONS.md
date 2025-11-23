# 📤 How to Share the Hierarchical Route Pipeline

## ✅ Yes, You Can Share It!

The `hierarchical-route-pipeline/` project is **fully portable and ready to share**. Everything needed is included:

- ✅ All source code
- ✅ Complete documentation
- ✅ Setup scripts (Windows & Linux/Mac)
- ✅ Configuration templates
- ✅ Dependencies list
- ✅ No hardcoded paths
- ✅ No sensitive data

## 🎯 Quick Share Instructions

### Option 1: Quick ZIP (Recommended)

**Windows:**
```powershell
# Navigate to project directory
cd "C:\Simplr projects\Route-optimization"

# Clean and prepare
cd hierarchical-route-pipeline
.\prepare_distribution.bat

# Go back to parent directory
cd ..

# Create ZIP
Compress-Archive -Path hierarchical-route-pipeline -DestinationPath hierarchical-route-pipeline-v1.0.0.zip -Force
```

**OR use Windows Explorer:**
1. Right-click on `hierarchical-route-pipeline` folder
2. Select "Send to" → "Compressed (zipped) folder"
3. Rename to: `hierarchical-route-pipeline-v1.0.0.zip`

### Option 2: Automated Cleanup + ZIP

**Windows:**
```batch
cd "C:\Simplr projects\Route-optimization\hierarchical-route-pipeline"
prepare_distribution.bat
cd ..
Compress-Archive -Path hierarchical-route-pipeline -DestinationPath hierarchical-route-pipeline-v1.0.0.zip
```

**Linux/Mac:**
```bash
cd "/path/to/Route-optimization/hierarchical-route-pipeline"
./prepare_distribution.sh
cd ..
tar -czf hierarchical-route-pipeline-v1.0.0.tar.gz hierarchical-route-pipeline/
```

## 📋 Before Sharing - Quick Checklist

Run this checklist (takes 2 minutes):

1. **Clean temporary files**
   ```
   cd hierarchical-route-pipeline
   prepare_distribution.bat   # Windows
   ./prepare_distribution.sh  # Linux/Mac
   ```

2. **Security check**
   - [ ] No `.env` file exists (only `.env.example`)
   - [ ] No database credentials in any files
   - [ ] No personal/sensitive data in logs

3. **Verify files** (should all exist)
   - [ ] README.md
   - [ ] requirements.txt
   - [ ] .env.example
   - [ ] config.py
   - [ ] run_pipeline.py
   - [ ] setup.bat and setup.sh
   - [ ] START_HERE.md

4. **Create ZIP/archive**

5. **Test the package** (optional but recommended)
   - Extract to new location
   - Run setup script
   - Verify documentation opens

## 📦 What Recipients Will Get

### Complete Package Contents
```
hierarchical-route-pipeline/
├── START_HERE.md          ← Recipients start here!
├── README.md              ← Complete documentation
├── QUICKSTART.md          ← 5-minute setup guide
├── requirements.txt       ← Python dependencies
├── .env.example          ← Configuration template
├── config.py             ← Settings
├── run_pipeline.py       ← Main program
├── setup.bat/.sh         ← Automated setup
├── src/                  ← Source code
│   ├── database.py
│   ├── pipeline.py
│   └── __init__.py
├── docs/                 ← Additional docs
└── logs/                 ← Empty (for their logs)
```

### What's NOT Included (Good!)
- ❌ No `.env` file (they create their own)
- ❌ No credentials
- ❌ No `venv/` or `__pycache__/`
- ❌ No old log files
- ❌ No sensitive data

## 🎁 Recipient Instructions

Share these quick steps with recipients:

### For Windows Users:
```
1. Extract hierarchical-route-pipeline-v1.0.0.zip
2. Open the folder and read START_HERE.md
3. Run: setup.bat
4. Edit .env with your database credentials
5. Open Command Prompt and run: python run_pipeline.py --test-mode
```

### For Linux/Mac Users:
```
1. Extract hierarchical-route-pipeline-v1.0.0.tar.gz
2. cd hierarchical-route-pipeline
3. Read START_HERE.md
4. Run: ./setup.sh
5. Edit .env with your database credentials
6. Run: python run_pipeline.py --test-mode
```

## 💡 Distribution Methods

### 1. Email (Small Organizations)
- Attach the ZIP file
- Include simple instructions
- Mention they should read START_HERE.md first

### 2. File Share (Cloud Storage)
- Upload to Google Drive / OneDrive / Dropbox
- Share the link
- Set appropriate permissions

### 3. Internal Server
- Place on shared network drive
- Document the location
- Set read permissions for team

### 4. Git Repository (Optional)
- Push to internal Git server
- Tag as v1.0.0
- Exclude .env in .gitignore (already done)

## ⚠️ Important Reminders

### For You (Distributor):
1. ✅ Always clean before sharing (run `prepare_distribution.bat/.sh`)
2. ✅ Never include `.env` with real credentials
3. ✅ Version your distributions (v1.0.0, v1.1.0, etc.)
4. ✅ Keep a copy for reference

### For Recipients:
1. They must create their own `.env` file
2. They need database access credentials
3. Python 3.8+ and ODBC Driver 17 required
4. They should start with test mode first

## 🧪 Testing the Package (Recommended)

Before sharing, test it:

1. **Extract to temp location**
   ```
   cd C:\Temp
   # Extract your ZIP here
   ```

2. **Run setup**
   ```
   cd hierarchical-route-pipeline
   setup.bat  # or ./setup.sh
   ```

3. **Verify**
   - All files present?
   - Setup runs without errors?
   - Documentation is readable?
   - No sensitive data visible?

## 📊 Package Size

Expected ZIP size: **~50-100 KB** (very small!)
- If much larger, you might have `venv/` or logs included
- Run `prepare_distribution.bat/.sh` to clean up

## 🆘 Troubleshooting

### "ZIP file is too large (>10 MB)"
**Problem:** Virtual environment or cache files included
**Solution:** Run `prepare_distribution.bat/.sh` again

### "Recipients can't run setup.bat"
**Problem:** Windows security or execution policy
**Solution:** Right-click → Properties → Unblock
Or run: `PowerShell -ExecutionPolicy Bypass -File setup.bat`

### "Can't extract the ZIP"
**Problem:** File corruption or wrong format
**Solution:** Try creating TAR.GZ for Linux/Mac users

## 📝 Version Tracking

When sharing updates:
1. Update version in CHANGELOG.md
2. Create new ZIP with version number
3. Communicate what changed
4. Keep old versions for rollback

Format: `hierarchical-route-pipeline-v{major}.{minor}.{patch}.zip`
- v1.0.0 - Initial release
- v1.0.1 - Bug fixes
- v1.1.0 - New features
- v2.0.0 - Breaking changes

## ✅ Final Verification

Before clicking "Send":

```
✓ Ran prepare_distribution script
✓ No .env file in package
✓ README.md is included and up-to-date
✓ START_HERE.md is included for recipients
✓ ZIP file is reasonably small (<1 MB)
✓ File named with version: hierarchical-route-pipeline-v1.0.0.zip
✓ Ready to share!
```

## 🎉 You're Ready!

The project is:
- ✅ Self-contained
- ✅ Well-documented
- ✅ Easy to setup
- ✅ Production-ready
- ✅ Safe to share

**Package it, share it, and let others benefit from your work!**

---

## Quick Commands Summary

**Prepare for distribution:**
```batch
cd hierarchical-route-pipeline
prepare_distribution.bat    # Windows
./prepare_distribution.sh   # Linux/Mac
```

**Create ZIP:**
```powershell
# Windows PowerShell
cd ..
Compress-Archive -Path hierarchical-route-pipeline -DestinationPath hierarchical-route-pipeline-v1.0.0.zip

# Linux/Mac
tar -czf hierarchical-route-pipeline-v1.0.0.tar.gz hierarchical-route-pipeline/
```

**Share with:**
```
1. Email attachment
2. Cloud storage link
3. Network drive
4. Git repository
```

---

**Created:** November 10, 2025
**Version:** 1.0.0
**Status:** Ready to Share ✅
