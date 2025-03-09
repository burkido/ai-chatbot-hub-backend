from fastapi import APIRouter, Response
import json

router = APIRouter()

@router.get("/.well-known/assetlinks.json")
async def serve_assetlinks_json():
    """
    Serve the assetlinks.json file required for Android App Links.
    
    Documentation: https://developer.android.com/training/app-links/verify-android-applinks
    """
    # Replace with your actual Android app package name
    package_name = "com.burkido.medicineai"
    
    # To get your SHA-256 fingerprint:
    # 1. For a debug build (development): 
    #    keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
    #
    # 2. For release build (if you've generated a keystore with Android Studio):
    #    keytool -list -v -keystore /path/to/your-app-release.keystore -alias your-key-alias
    #
    # The fingerprint will look something like:
    # "FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:6F:89:9B:83:32:66:75:91:03:3B:9C"
    
    # Replace with your actual fingerprint(s)
    sha256_cert_fingerprints = [
        "7E:DA:FE:A4:35:1A:11:54:27:00:EF:AD:B7:D2:F8:BD:0C:96:6C:21:1E:F0:19:B7:81:AC:62:40:13:BC:6F:E3"
    ]
    
    assetlinks_content = generate_assetlinks_json(
        package_name=package_name, 
        sha256_cert_fingerprints=sha256_cert_fingerprints
    )
    
    return Response(
        content=assetlinks_content,
        media_type="application/json"
    )

def generate_assetlinks_json(package_name: str, sha256_cert_fingerprints: list[str]) -> str:
    """
    Generate the assetlinks.json content for Android App Links.
    
    Args:
        package_name: The Android app package name
        sha256_cert_fingerprints: List of SHA256 fingerprints of the app's signing certificate
        
    Returns:
        JSON string containing the Digital Asset Links declaration
    """
    assetlinks_content = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": package_name,
                "sha256_cert_fingerprints": sha256_cert_fingerprints
            }
        }
    ]
    return json.dumps(assetlinks_content, indent=2)
