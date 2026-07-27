import { useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "../api/datasets";

export function useUpload(onUploaded: (id: string) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => datasetsApi.upload(file),
    onSuccess: (meta) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      onUploaded(meta.id);
    },
  });
}
