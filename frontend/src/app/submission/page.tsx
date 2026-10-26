"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { DocumentItem, DocumentSectionItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import {
  Upload,
  Lock,
  Trash2,
  FileText,
  AlertTriangle,
  Eye,
  CheckCircle2,
} from "lucide-react";

export default function SubmissionVaultPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [sections, setSections] = useState<DocumentSectionItem[]>([]);
  const [docType, setDocType] = useState<string>("technical_disclosure");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = async () => {
    if (!selectedTechId) return;
    setError(null);
    try {
      const docs = await apiClient.listDocuments(selectedTechId, true);
      setDocuments(docs);
      const active = docs.find((d) => !d.is_deleted) || null;
      if (active) {
        await inspectSections(active);
      } else {
        setSelectedDoc(null);
        setSections([]);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const inspectSections = async (doc: DocumentItem) => {
    setSelectedDoc(doc);
    if (doc.is_deleted) {
      setSections([]);
      return;
    }
    try {
      const secs = await apiClient.getDocumentSections(doc.id);
      setSections(secs);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [selectedTechId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTechId || !selectedFile) return;
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const uploaded = await apiClient.uploadDocument(
        selectedTechId,
        docType,
        selectedFile
      );
      setMessage(
        `Uploaded & encrypted "${uploaded.original_filename}" (SHA-256: ${uploaded.sha256_hash.slice(
          0,
          16
        )}...)`
      );
      setSelectedFile(null);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (doc: DocumentItem) => {
    setError(null);
    setMessage(null);
    try {
      const res = await apiClient.deleteDocument(
        doc.id,
        "Analyst requested complete cascade purge from vault, chunks, embeddings, and active evidence."
      );
      setMessage(
        `Cascade deleted "${doc.original_filename}": ${res.sections_removed} sections removed, ${res.chunks_removed} embeddings purged.`
      );
      await loadDocuments();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t.nav.submission}</h1>
        <p className="text-sm text-slate-600">
          {lang === "id"
            ? "Brankas dokumen terenkripsi (Fernet AES-128-CBC + HMAC-SHA256) di luar web root dengan verifikasi magic-byte dan penghapusan kaskade penuh."
            : "Encrypted document vault outside web root (.runtime/vault) with magic-byte verification, OCR detection, and complete cascade deletion."}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}
      {message && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-xs text-emerald-900">
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload Form */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <Upload className="h-4 w-4 text-blue-700" />
            <span>
              {lang === "id" ? "Unggah Dokumen Bukti" : "Upload Evidence Document"}
            </span>
          </div>
          <p className="text-xs text-slate-600">
            Allowed formats: <code>.pdf</code>, <code>.docx</code>, <code>.txt</code>,{" "}
            <code>.md</code> (Max 25 MB). Executable and mismatched signatures are
            rejected.
          </p>
          <form onSubmit={handleUpload} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Document Category
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-xs"
              >
                <option value="patent_specification">Patent Specification & Claims</option>
                <option value="technical_disclosure">
                  Technical Disclosure & Pilot Validation
                </option>
                <option value="market_study">Market & Commercialization Study</option>
                <option value="regulatory_dossier">Regulatory & TKDN Dossier</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Select File
              </label>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="mt-1 block w-full text-xs text-slate-700 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>
            <Button
              type="submit"
              disabled={!selectedFile || uploading}
              className="w-full"
            >
              <Lock className="h-3.5 w-3.5" />
              {uploading ? "Encrypting & Parsing..." : "Verify & Store in Encrypted Vault"}
            </Button>
          </form>
        </Card>

        {/* Vault Document List */}
        <Card className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              {lang === "id"
                ? "Inventaris Brankas Dokumen & Hash SHA-256"
                : "Encrypted Vault Inventory & SHA-256 Hashes"}
            </h2>
            <Badge variant="info">
              {documents.filter((d) => !d.is_deleted).length} Active Documents
            </Badge>
          </div>

          <div className="divide-y divide-slate-200">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className={`py-3 flex flex-wrap items-start justify-between gap-3 ${
                  doc.is_deleted ? "opacity-50" : ""
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-700" />
                    <span className="font-bold text-sm text-slate-900">
                      {doc.original_filename}
                    </span>
                    <Badge variant="outline">{doc.document_type}</Badge>
                    {doc.encrypted_at_rest && (
                      <Badge variant="success">
                        <Lock className="h-3 w-3" /> Encrypted
                      </Badge>
                    )}
                    {doc.ocr_required && (
                      <Badge variant="warning">
                        <AlertTriangle className="h-3 w-3" /> OCR Required (Scanned PDF)
                      </Badge>
                    )}
                    {doc.is_deleted && <Badge variant="danger">Cascade Deleted</Badge>}
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
                    SHA-256: {doc.sha256_hash}
                  </div>
                  <div className="text-xs text-slate-600">
                    Sections/Pages: <strong>{doc.page_or_section_count}</strong> •
                    Extracted chars: <strong>{doc.extracted_char_count}</strong> • Size:{" "}
                    {(doc.file_size_bytes / 1024).toFixed(1)} KB
                  </div>
                  {doc.ocr_warning_message && (
                    <div className="rounded bg-amber-50 border border-amber-200 px-2.5 py-1 text-xs text-amber-900">
                      {doc.ocr_warning_message}
                    </div>
                  )}
                </div>

                {!doc.is_deleted && (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => inspectSections(doc)}
                    >
                      <Eye className="h-3.5 w-3.5" /> Locators
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDelete(doc)}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Cascade Delete
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Parsed Source Location Viewer */}
      {selectedDoc && (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Source Location Resolution Index — {selectedDoc.original_filename}
              </h3>
              <p className="text-xs text-slate-500">
                Every evidence item in TechVal AI must resolve to one of these canonical
                locators (<code>page:N</code>, <code>para:N</code>, or <code>table:N</code>
                ) and contain an exact substring match.
              </p>
            </div>
            <Badge variant="success">
              <CheckCircle2 className="h-3 w-3" /> {sections.length} Resolved Locators
            </Badge>
          </div>

          <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto pr-1">
            {sections.map((sec) => (
              <div
                key={sec.id}
                className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-blue-700">
                    [{sec.location_ref}] {sec.heading || ""}
                  </span>
                  <span className="text-slate-500">{sec.char_count} chars</span>
                </div>
                <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed">
                  {sec.content_text}
                </pre>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
