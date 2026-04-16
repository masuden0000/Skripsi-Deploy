# Skripsi_Dummy-Experiments

Repository untuk eksperimen PyMuPDF4LLM + RAG dengan backend Supabase dan frontend interaktif.

## Update Terbaru

### ✅ Security & Configuration
- **Environment Management**: Menambahkan `.gitignore` untuk file sensitif (`.env`, `.pdf`, `.venv`)
- **Template Environment**: Membuat `.env.example` sebagai template konfigurasi aman tanpa secret values
- **Secret Management**: Menonaktifkan API keys lama dan menyiapkan placeholder untuk regenerasi

### ✅ Python Version Support
- **Runtime Validation**: Menambahkan function `ensure_supported_python()` di `manage.py`
- **Version Constraint**: Project mendukung Python 3.11 hingga 3.13 saja
  - Reject Python < 3.11 (legacy)
  - Reject Python >= 3.14 (belum tested)
- **Early Error Detection**: Validasi dilakukan saat startup untuk fail fast

### ✅ Dependency Management
- **Version Pinning**: Menambahkan version constraint ke semua dependencies di `requirements.txt`
  - `langchain-text-splitters>=0.3,<0.4`
  - `langchain-core>=0.3,<0.4`
  - `langchain-google-genai>=2.1,<3`
  - `python-dotenv>=1.0,<2`
  - `pydantic>=2.10,<3`
  - `supabase>=2.9,<3`
- **Reproducibility**: Memastikan consistency di berbagai environment

### ✅ Import Logic Refactor
- **chat_server.py**: Ganti `try/except ImportError` dengan `if __package__` untuk relative/absolute import
- **extractor.py**: Konsisten dengan pattern import yang lebih robust
- **Result**: Better module discovery dan lebih mudah di-debug

### ✅ Environment Loading
- **Explicit Load**: Tambahkan `load_dotenv(dotenv_path=ENV_FILE)` di `chat_server.py` untuk explicit .env handling
- **Consistent Path**: Menggunakan `APP_DIR / ".env"` untuk path loading yang reliable

### ✅ Modular Refactor (model_ai)
- **Struktur Baru**: Memecah modul AI ke subpackage terpisah agar lebih maintainable:
   - `model_ai/loader/` untuk extraction, chunk building, dan Supabase ingest
   - `model_ai/rag/` untuk RAG service dan simple LLM flow
   - `model_ai/ui/` untuk server chat
   - `model_ai/dev/` untuk script inspeksi/dev helper
- **Cleanup Legacy**: Menghapus file modul lama yang duplikatif di root `model_ai/`

### ✅ Chunk Quality Improvements
- **Page Range Accuracy**: Memperbaiki urutan chunk dan rentang halaman di `data/output_chunks.json`
- **OCR Artifact Cleanup**: Mengurangi artefak strikethrough/noise hasil OCR pada konten chunk
- **Output Refresh**: Regenerasi `data/output.md` agar sinkron dengan pipeline terbaru

## Quick Start

1. Clone repository:
   ```bash
   git clone https://github.com/masuden0000/Skripsi_Dummy-Experiments-.git
   cd Skripsi_Dummy-Experiments-
   ```

2. Setup environment:
   ```bash
   cp experiments/pymupdf4llm/.env.example experiments/pymupdf4llm/.env
   # Edit .env dengan nilai API keys dan Supabase credentials Anda
   ```

3. Create virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   # atau: source .venv/bin/activate  # Linux/macOS
   ```

4. Install dependencies:
   ```bash
   cd experiments/pymupdf4llm
   pip install -r requirements.txt
   ```

5. Run setup dan RAG server:
   ```bash
   python manage.py --setup
   python manage.py --chat
   ```

## Project Structure

```
experiments/
├── pdftext/              # PDF text extraction experiments
├── pymupdf4llm/          # Main RAG system
│   ├── model_ai/         # Core AI logic (LLM, RAG, embeddings)
│   ├── frontend/         # Web UI (HTML, CSS, JS)
│   ├── data/             # Processed chunks and embeddings
│   ├── manage.py         # CLI entry point
│   └── requirements.txt   # Python dependencies
```

## Python Support

- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13
- ❌ Python 3.14+ (not tested yet)
- ❌ Python < 3.11 (legacy)

## Requirements

- Google AI API Key (Gemini)
- Supabase project (for embeddings storage)
- Python 3.11 or higher

## Notes

- Jangan commit `.env` file, selalu gunakan `.env.example` sebagai template
- Cache Python (`__pycache__`, `.pyc`) di-ignore dari repository
- PDF files diabaikan dari version control
