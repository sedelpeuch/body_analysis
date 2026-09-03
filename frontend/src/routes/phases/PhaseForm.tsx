import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { useCreatePhaseMutation, useUpdatePhaseMutation } from "../../api/phases/hooks";
import { ApiError } from "../../api/client";
import type { PhaseKind, PhaseOut } from "../../api/types";

export interface PhaseFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  phase?: PhaseOut;
}

const KIND_LABELS: Record<PhaseKind, string> = {
  free: "Libre",
  bulk: "Prise de masse",
  cut: "Sèche",
  maintain: "Maintien",
};

function toNullableNumber(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

export function PhaseForm({ open, onOpenChange, phase }: PhaseFormProps) {
  const [name, setName] = useState(phase?.name ?? "");
  const [kind, setKind] = useState<PhaseKind>(phase?.kind ?? "cut");
  const [startsOn, setStartsOn] = useState(phase?.starts_on ?? "");
  const [endsOn, setEndsOn] = useState(phase?.ends_on ?? "");
  const [weightTarget, setWeightTarget] = useState(phase?.weight_target_kg?.toString() ?? "");
  const [bodyFatTarget, setBodyFatTarget] = useState(phase?.body_fat_target_pct?.toString() ?? "");
  const [muscleTarget, setMuscleTarget] = useState(phase?.skeletal_muscle_target_kg?.toString() ?? "");
  const [caloriesTarget, setCaloriesTarget] = useState(phase?.daily_calories_target?.toString() ?? "");
  const [notes, setNotes] = useState(phase?.notes ?? "");
  const [validationError, setValidationError] = useState<string | null>(null);

  const createMutation = useCreatePhaseMutation();
  const updateMutation = useUpdatePhaseMutation(phase?.id ?? 0);
  const mutation = phase ? updateMutation : createMutation;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setValidationError(null);
    if (endsOn < startsOn) {
      setValidationError("La date de fin doit être postérieure ou égale à la date de début.");
      return;
    }
    const body = {
      name,
      kind,
      starts_on: startsOn,
      ends_on: endsOn,
      weight_target_kg: toNullableNumber(weightTarget),
      body_fat_target_pct: toNullableNumber(bodyFatTarget),
      skeletal_muscle_target_kg: toNullableNumber(muscleTarget),
      daily_calories_target: toNullableNumber(caloriesTarget),
      notes: notes.trim() === "" ? null : notes,
    };
    mutation.mutate(body, { onSuccess: () => onOpenChange(false) });
  }

  const serverError = mutation.error instanceof ApiError ? mutation.error.problem.detail : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{phase ? "Modifier la phase" : "Nouvelle phase"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <Input placeholder="Nom" value={name} onChange={(e) => setName(e.target.value)} required />
          <Select value={kind} onValueChange={(v) => setKind(v as PhaseKind)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(KIND_LABELS) as PhaseKind[]).map((k) => (
                <SelectItem key={k} value={k}>
                  {KIND_LABELS[k]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex gap-2">
            <Input type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} required />
            <Input type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input
              type="number"
              step="0.1"
              placeholder="Objectif poids (kg)"
              value={weightTarget}
              onChange={(e) => setWeightTarget(e.target.value)}
            />
            <Input
              type="number"
              step="0.1"
              placeholder="Objectif masse grasse (%)"
              value={bodyFatTarget}
              onChange={(e) => setBodyFatTarget(e.target.value)}
            />
            <Input
              type="number"
              step="0.1"
              placeholder="Objectif muscle (kg)"
              value={muscleTarget}
              onChange={(e) => setMuscleTarget(e.target.value)}
            />
            <Input
              type="number"
              placeholder="Objectif calories/jour"
              value={caloriesTarget}
              onChange={(e) => setCaloriesTarget(e.target.value)}
            />
          </div>
          <Input placeholder="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />

          {(validationError ?? serverError) && (
            <p className="text-sm text-destructive">{validationError ?? serverError}</p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Enregistrement…" : "Enregistrer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
