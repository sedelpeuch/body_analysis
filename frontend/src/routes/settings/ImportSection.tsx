import { useState } from "react";
import { useImportRun, useImportRuns, useUploadZipMutation } from "../../api/imports/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { Button } from "../../components/ui/button";
import { ApiError } from "../../api/client";

export function ImportSection() {
  const [file, setFile] = useState<File | null>(null);
  const [runId, setRunId] = useState<number | undefined>(undefined);

  const uploadMutation = useUploadZipMutation();
  const currentRun = useImportRun(runId, { pollWhileRunning: true });
  const history = useImportRuns();

  function handleUpload() {
    if (!file) return;
    uploadMutation.mutate(file, { onSuccess: (run) => setRunId(run.id) });
  }

  const uploadError = uploadMutation.error instanceof ApiError ? uploadMutation.error.problem.detail : null;

  return (
    <DomainCard variant="phase" title="Import Samsung Health (ZIP)">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-text-mid"
          />
          <Button onClick={handleUpload} disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? "Envoi…" : "Importer"}
          </Button>
        </div>

        {uploadError && <p className="text-sm text-destructive">{uploadError}</p>}

        {currentRun.data && (
          <div className="tabular text-sm">
            <p>
              Statut : <span className="text-text-high">{currentRun.data.status}</span>
            </p>
            {currentRun.data.status === "success" && currentRun.data.counts && (
              <pre className="mt-1 whitespace-pre-wrap text-xs text-text-mid">
                {JSON.stringify(currentRun.data.counts, null, 2)}
              </pre>
            )}
            {currentRun.data.status === "failed" && currentRun.data.error && (
              <p className="text-destructive">{currentRun.data.error}</p>
            )}
          </div>
        )}

        <div>
          <h4 className="mb-2 text-sm text-text-mid">Historique</h4>
          <ul className="flex flex-col gap-1">
            {history.data?.map((run) => (
              <li key={run.id} className="tabular flex justify-between text-xs text-text-mid">
                <span>{run.source_name}</span>
                <span>{run.status}</span>
                <span>{new Date(run.started_at).toLocaleString("fr-FR")}</span>
                <span>{run.finished_at ? new Date(run.finished_at).toLocaleString("fr-FR") : "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </DomainCard>
  );
}
