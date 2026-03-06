# 1. 베이스 이미지 선택
# NVIDIA 공식 CUDA 이미지를 사용합니다. 'devel' 태그는 컴파일러(nvcc) 등 개발 도구가 포함된 버전입니다.
# RTX A6000에 최적화된 최신 버전을 사용하기 위해 CUDA 12.4.1을 선택합니다.
# 베이스 OS는 안정적인 Ubuntu 22.04를 사용합니다.
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# 2. 환경 변수 설정
# noninteractive 설정을 통해 apt-get 등 설치 시 사용자 입력 없이 자동으로 진행되도록 합니다.
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

# 3. 기본 패키지 설치
# 컨테이너 내에서 필요한 기본 도구를 설치합니다.
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    vim \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 4. uv 설치 (Rust 기반 - Python 불필요)
# uv는 단일 바이너리로 제공되어 빠르고 안정적입니다.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 5. Python 설치 (uv로 관리)
# uv를 통해 Python 3.12를 설치합니다.
RUN uv python install 3.12

# python 심볼릭 링크 생성
RUN ln -s $(uv python find 3.12) /usr/bin/python && \
    ln -s $(uv python find 3.12) /usr/bin/python3

# 6. Node.js 22.x LTS 설치
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    rm -rf /var/lib/apt/lists/*

# 7. 작업 디렉토리 설정
WORKDIR /workspace

# 8. pyproject.toml 복사 및 의존성 설치
# 의존성 파일을 먼저 복사하여 Docker 레이어 캐싱을 최적화합니다.
# COPY pyproject.toml uv.lock* ./

# 9. uv로 가상환경 생성 및 의존성 설치 (초고속)
# PyTorch와 기타 라이브러리를 uv로 설치합니다.
RUN uv venv /workspace/.venv && \
    uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 && \
    uv pip install jupyterlab pandas numpy scikit-learn matplotlib

# 10. 환경 변수 설정
# 가상환경을 자동으로 활성화합니다.
ENV PATH="/workspace/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/workspace/.venv"

# 11. 컨테이너 실행 시 기본 명령어
# 컨테이너가 종료되지 않고 계속 실행되도록 유지하며, 사용자가 exec로 접속할 수 있게 합니다.
CMD ["tail", "-f", "/dev/null"]
