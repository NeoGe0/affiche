export function fontBaseName(fileName: string): string {
  return fileName.replace(/\.(ttf|otf)$/i, '');
}
