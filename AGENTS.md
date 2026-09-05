# Development Environment Constraints


## PowerShell Environment

The project is developed on Windows.

Default shell:
Windows PowerShell 5.1


Do NOT generate PowerShell 7-only syntax.

Avoid:

- Invoke-RestMethod -Form
- PowerShell Core specific features


For multipart file upload testing:

Use:

curl.exe -F

or Python requests.


Example:

curl.exe `
  -X POST `
  "http://127.0.0.1:8000/documents" `
  -F "file=@path/to/file.pdf"


Before generating shell commands:
- consider Windows PowerShell compatibility
- avoid assuming PowerShell 7
- provide commands runnable in the current environment