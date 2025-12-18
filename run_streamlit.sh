#!/bin/bash
set -e

IMAGE_NAME="data-monitoring"
CONTAINER_NAME="data-monitoring"
PORT=8501

export AWS_PROFILE=prod   # 또는 IAM Role

echo "🚀 Streamlit Viewer 실행 스크립트 시작"

# 1️⃣ 기존 컨테이너 정리
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "🧹 기존 컨테이너 정리 중..."
    docker stop ${CONTAINER_NAME} >/dev/null 2>&1 || true
    docker rm ${CONTAINER_NAME} >/dev/null 2>&1 || true
fi

# 2️⃣ Docker 이미지 존재 여부 확인 및 빌드
if [ ! "$(docker images -q ${IMAGE_NAME} 2> /dev/null)" ]; then
    echo "📦 이미지가 없어서 새로 빌드합니다..."
    docker build -t ${IMAGE_NAME} .
else
    echo "✅ 기존 이미지 사용 (${IMAGE_NAME})"
fi

# 3️⃣ 컨테이너 실행 (로컬 소스코드 실시간 반영)
echo "▶️ Streamlit 서버 실행 중..."
docker run -d \
  -p ${PORT}:8501 \
  -v $(pwd):/app \
  -v "/Users/benjamin/PycharmProjects/airflow/data":"/app/data" \
  --name ${CONTAINER_NAME} \
  -v ~/.aws:/root/.aws:ro \
  --network airflow_default \
  ${IMAGE_NAME}


# 4️⃣ 실행 상태 확인
sleep 2
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✅ Streamlit 실행 완료!"
    echo "🌐 http://localhost:${PORT} 에 접속하세요."
else
    echo "❌ 컨테이너 실행 실패. 로그를 확인하세요."
    docker logs ${CONTAINER_NAME}
fi
