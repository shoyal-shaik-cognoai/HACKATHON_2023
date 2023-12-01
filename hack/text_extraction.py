from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from hack.models import CandidateProfile
print('infile')
import time
url = "https://few-areas-spend.loca.lt/media/abc.pdf"

endpoint = "https://chat-pdf-poc-form-recog.cognitiveservices.azure.com/"
key = "eb5cd517e2d74a4da3fa3538397147c4"

def format_bounding_region(bounding_regions):
    if not bounding_regions:
        return "N/A"
    return ", ".join("Page #{}: {}".format(region.page_number, format_polygon(region.polygon)) for region in bounding_regions)

def format_polygon(polygon):
    if not polygon:
        return "N/A"
    return ", ".join(["[{}, {}]".format(p.x, p.y) for p in polygon])

def analyze_general_documents(name, phone, file_path):
    if CandidateProfile.objects.filter(file_path=file_path).first():
        print('already processed')
        return
    document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(file_path, 'rb') as file:
        pdf_bytes = file.read()
    poller = document_analysis_client.begin_analyze_document(
            "prebuilt-document", pdf_bytes)
    result = poller.result()

    cv_content = result.content

    CandidateProfile.objects.get_or_create(file_path=file_path, candidate_name=name, phone_number=phone, defaults={'cv_content': cv_content})
    print('Sucessfully processed')
