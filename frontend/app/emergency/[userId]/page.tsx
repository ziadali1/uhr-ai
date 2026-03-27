export default function EmergencyPage({ params }: { params: { userId: string } }) {
  return (
    <div className="min-h-screen bg-red-50 p-4">
      <div className="mx-auto max-w-md space-y-4 rounded-2xl border border-red-200 bg-white p-6 shadow-lg">
        <div className="flex items-center gap-2 text-red-600">
          <span className="text-2xl">🚨</span>
          <h1 className="text-xl font-bold">EMERGÊNCIA</h1>
        </div>

        <p className="text-xs text-gray-500">
          Perfil de emergência disponível na Fase 4. ID: {params.userId}
        </p>

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs text-amber-800">
            Esta página será pública e acessível via QR Code, sem necessidade de login,
            exibindo alergias, medicamentos em uso e condições ativas do paciente.
          </p>
        </div>
      </div>
    </div>
  );
}
