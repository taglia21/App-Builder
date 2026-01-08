export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-6 p-8 border rounded-lg shadow-lg bg-card text-card-foreground max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight text-primary">TestDash</h1>
        <p className="text-xl text-muted-foreground">A test dashboard app</p>
        <div className="flex justify-center gap-4">
          <a href="/login" className="px-8 py-3 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition font-medium">
            Get Started
          </a>
          <a href="/docs" className="px-8 py-3 bg-secondary text-secondary-foreground rounded-md hover:opacity-90 transition font-medium">
            Documentation
          </a>
        </div>
      </div>
    </div>
  );
}
