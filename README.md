# CTT Viewer (BHSA/Text-Fabric)

플라스크 기반 웹 앱으로 CTT 파일과 BHSA(Text-Fabric) 데이터를 트리 형태로 탐색합니다.

## Windows

### 준비물
- Git
- 인터넷만 연결되어 있으면 `start_viewer.bat`이 필요한 Python과 패키지를 자동으로 설치합니다.

### 설치 및 실행
```powershell
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
start_viewer.bat        # 또는 PowerShell: .\setup_windows.ps1 -AutoInstall
```
실행 후 브라우저에서 <http://127.0.0.1:5001/> 를 열어 “TF gloss 사용 가능” 메시지를 확인하세요.

## macOS / Linux

### 준비물
- Git
- Python 3.9 이상 (macOS는 `brew install python`)

### 설치 및 실행
```bash
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
./run.sh                # 최초 실행 시 venv 및 의존성 자동 설치
```
권한 오류가 발생하면 `chmod +x run.sh` 후 다시 실행하세요. 서버가 뜨면 브라우저에서 <http://127.0.0.1:5001/> 를 확인합니다.

## Docker (선택)

```bash
docker build -t ctt-viewer .
docker run --rm -p 5001:5001 -v $(pwd)/data:/app/data ctt-viewer
```

## 추가 문서

- `README-RUN.txt` : 실행 스크립트 상세
- `README-RUN-windows.txt`, `README-RUN-macOS.txt` : 운영체제별 안내
