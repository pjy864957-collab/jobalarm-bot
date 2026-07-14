import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, messaging
import json

# =====================================================================
# 1. 초기 세팅 (본인의 정보로 반드시 수정해야 하는 부분!)
# =====================================================================

# 1) 파이어베이스 비밀키 파일 이름 (main.py와 같은 폴더에 있어야 합니다)
key_file_name = "firebase_key.json"

# 2) 구글 AI 스튜디오에서 발급받은 API 키
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# =====================================================================

# 파이어베이스 초기화 (프로그램 실행 시 한 번만)
if not firebase_admin._apps:
    cred = credentials.Certificate(key_file_name)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 제미나이 AI 초기화 (가장 빠르고 가벼운 1.5-flash 모델 사용)
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')


def analyze_unprocessed_jobs():
    print("🤖 AI 분석 및 알림 엔진 가동을 시작합니다...")

    # 파이어베이스에서 'AI분석여부'가 False인 공고를 가져옵니다.
    # (과부하 방지를 위해 한 번에 5개씩만 가져옵니다)
    docs = db.collection('jobs').where('AI분석여부', '==', False).limit(5).stream()

    has_docs = False

    for doc in docs:
        has_docs = True
        doc_id = doc.id
        job_data = doc.to_dict()

        job_title = job_data.get("공고명", "")
        brand_name = job_data.get("상표명", "")

        print(f"\n🔍 [AI 분석 중] {brand_name} - {job_title}")

        # -----------------------------------------------------------------
        # 2. AI에게 내리는 명령서 (프롬프트 세팅)
        # -----------------------------------------------------------------
        prompt = f"""
        당신은 커피 업계 전문 채용 분석 AI입니다.
        아래 채용 공고 정보를 분석하여 완벽한 JSON 형식으로만 답변해 주세요.

        [채용 공고]
        회사(상표명): {brand_name}
        공고명: {job_title}

        [분석 기준]
        1. 이 공고가 단순 홀 서비스나 서빙 바리스타가 아닌, 직접 생두 로스팅을 하거나 로스팅 설비(프로밧, 기센 등)를 다루는 '전문 로스터(Roaster)' 포지션인지 판단하세요.
        2. 공고 내용에서 특별한 우대 요건(예: EUCA 자격증, 디플로마, 로스터 경력 등)이 유추되면 요약해 주세요.

        [출력 JSON 형식]
        {{
            "is_roaster_job": true 또는 false,
            "matching_score": 0~100 사이의 숫자 (로스터 전문 직무일수록 높은 점수),
            "key_requirements": "우대 자격증 및 경력 요약 (없으면 '없음')",
            "ai_summary": "공고에 대한 한 줄 핵심 평"
        }}

        주의: JSON 형식 외의 다른 인사말이나 설명은 절대 포함하지 마세요.
        """

        try:
            # AI에게 분석 요청 (답변을 JSON 형식으로 강제함)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            # AI의 답변 텍스트를 파이썬 사전(dict) 데이터로 변환
            ai_result = json.loads(response.text)

            # -----------------------------------------------------------------
            # 3. 분석 결과 DB 업데이트 및 푸시 알림 발송 조건 확인
            # -----------------------------------------------------------------
            updated_data = {
                "AI분석여부": True,
                "로스터직무여부": ai_result.get("is_roaster_job", False),
                "적합도점수": ai_result.get("matching_score", 0),
                "우대요건": ai_result.get("key_requirements", "없음"),
                "AI한줄요약": ai_result.get("ai_summary", "")
            }

            # 1) 파이어베이스 데이터 업데이트
            db.collection('jobs').document(doc_id).update(updated_data)
            print(f"✅ DB 업데이트 완료! (점수: {updated_data['적합도점수']}점)")

            # 2) 조건에 맞으면 스마트폰으로 푸시 알림(FCM) 쏘기
            # (조건: 진짜 로스터 직무이면서, AI 적합도 점수가 80점 이상일 때)
            if updated_data['로스터직무여부'] == True and updated_data['적합도점수'] >= 80:
                print(f"🔔 고득점 공고 발견! 어플로 푸시 알림을 발송합니다.")

                message = messaging.Message(
                    notification=messaging.Notification(
                        title=f"☕ 새로운 맞춤 로스터 채용: {brand_name}",
                        body=f"{job_title}\n{updated_data['AI한줄요약']}"
                    ),
                    topic="roaster_alert"  # 이 주제를 구독하는 어플에 전부 알림을 보냅니다.
                )

                messaging.send(message)
                print("📨 푸시 알림 발송 완료!")

        except Exception as e:
            print(f"❌ 분석 또는 알림 실패 ({doc_id}): {e}")

    if not has_docs:
        print("\n💡 새로 분석할 공고가 없습니다. 크롤러(main.py)를 먼저 실행해 주세요.")


# 이 파이썬 파일을 실행할 때 바로 작동하게 하는 부분
if __name__ == "__main__":
    analyze_unprocessed_jobs()
