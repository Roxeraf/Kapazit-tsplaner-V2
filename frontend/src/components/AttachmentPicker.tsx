export default function AttachmentPicker({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  const addFiles = (list: FileList | null) => {
    if (!list) return;
    onChange([...files, ...Array.from(list)]);
  };

  const removeFile = (index: number) => onChange(files.filter((_, i) => i !== index));

  return (
    <div>
      <input
        type="file"
        multiple
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
        style={{ fontSize: "0.85rem" }}
      />
      {files.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: "0.5rem 0 0", fontSize: "0.85rem" }}>
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} style={{ display: "flex", justifyContent: "space-between", padding: "0.2rem 0" }}>
              <span>📎 {f.name}</span>
              <button
                type="button"
                onClick={() => removeFile(i)}
                style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
