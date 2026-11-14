export function DemoVideo() {
  return (
    <section aria-label="CaseTwin demo video" className="space-y-4">
      <div className="aspect-video w-full overflow-hidden rounded-xl border border-zinc-200 bg-zinc-950 shadow-sm">
        <iframe
          className="h-full w-full"
          src="https://www.youtube-nocookie.com/embed/7vBo-Qunr3o?rel=0&playsinline=1"
          title="CaseTwin product demo"
          loading="eager"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </div>
      <p className="text-sm leading-relaxed text-zinc-600">
        See the full workflow, from chest X-ray upload to case comparison and referral drafting.
        Then try it yourself using Download sample case in the Clinical Copilot.
      </p>
      <a
        href="https://www.youtube.com/watch?v=7vBo-Qunr3o"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex text-xs font-medium text-blue-600 underline underline-offset-4 hover:text-blue-800"
      >
        Open demo on YouTube
      </a>
    </section>
  );
}
