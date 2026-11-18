import "./globals.css";

export const metadata = {
  title: "AlertaBairro",
  description: "Relatos colaborativos de alagamento em São Paulo",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
