import { useNandQuery } from "@/lib/nandbank/query";
import { gateway, DEMO_MODE } from "@/services/api/client";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Lista de filiais autorizadas, obtida do backend; nunca inventa códigos locais. */
export function GatewayBranchPicker({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const config = useNandQuery(["public-config"], gateway.config);
  const regions = config.data?.regions ?? [];
  const loaded = regions.some((region) => region.branches.length > 0);

  return (
    <div>
      <Select
        value={value || undefined}
        onValueChange={onChange}
        disabled={disabled || DEMO_MODE || !loaded}
      >
        <SelectTrigger className="min-h-11" aria-label="Seleccionar filial">
          <SelectValue placeholder={config.isPending ? "A carregar filiais..." : "Seleccione a filial"} />
        </SelectTrigger>
        <SelectContent>
          {regions.map((region) => (
            <SelectGroup key={region.code}>
              <SelectLabel>{region.name}</SelectLabel>
              {region.branches.map((branch) => (
                <SelectItem key={branch.code} value={branch.code}>
                  {branch.city} · {branch.country} ({branch.code}) · {branch.suggested_currency}
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>
      {config.isError && (
        <p role="alert" className="form-message form-message-error">
          Não foi possível obter as filiais. Confirme a ligação ao Gateway.
          <button type="button" className="underline ml-2" onClick={() => void config.refetch()}>
            Tentar novamente
          </button>
        </p>
      )}
      {!config.isPending && !config.isError && !loaded && !DEMO_MODE && (
        <p role="status" className="field-note">Nenhuma filial foi disponibilizada pelo Gateway.</p>
      )}
    </div>
  );
}
