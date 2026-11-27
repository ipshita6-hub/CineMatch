import { motion, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import Poster from './Poster'

export default function AnimatedMarqueeHero({ movies = [], loading = false }) {
  const reduced = useReducedMotion()
  const words = ['Find', 'your', 'next', 'favorite', 'story.']
  return (
    <section className="marquee-hero relative flex min-h-[760px] flex-col items-center overflow-hidden px-4 pt-20 text-center sm:min-h-[820px] sm:pt-24">
      <div className="relative z-10 flex max-w-4xl flex-col items-center">
        <motion.div initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-plum-600 backdrop-blur-sm"><Sparkles size={15} className="text-rose-600" /> Your personal movie universe</motion.div>
        <motion.h1 initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: reduced ? 0 : 0.1 } } }} className="mt-7 text-5xl font-extrabold leading-[1.03] tracking-tight text-white sm:text-7xl lg:text-8xl">
          {words.map((word) => <motion.span key={word} variants={{ hidden: reduced ? { opacity: 1 } : { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 20 } } }} className="inline-block">{word}&nbsp;</motion.span>)}
        </motion.h1>
        <motion.p initial={reduced ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduced ? 0 : 0.5 }} className="mt-6 max-w-xl text-base leading-relaxed text-plum-600 sm:text-lg">Discover movies picked for you, powered by patterns learned from 20 million real ratings.</motion.p>
        <motion.div initial={reduced ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduced ? 0 : 0.65 }} className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/register" className="rounded-full bg-rose-500 px-8 py-3.5 text-sm font-bold text-white shadow-lg shadow-purple-950/50 transition hover:scale-105 hover:bg-rose-600 active:scale-95">Get started</Link>
          <Link to="/login" className="rounded-full border border-white/20 bg-white/5 px-8 py-3.5 text-sm font-semibold text-white transition hover:bg-white/10">Sign in</Link>
        </motion.div>
      </div>
      <div className="marquee-mask absolute inset-x-0 bottom-0 h-[270px] sm:h-[320px]" aria-label="Featured movies">
        {movies.length > 0 ? <div className="marquee-track">{[0, 1].map((copy) => <div key={copy} className="marquee-group" aria-hidden={copy === 1}>{movies.map((movie, index) => <div key={`${copy}-${movie.movie_id}`} className="marquee-poster" style={{ transform: `rotate(${index % 2 ? 4 : -3}deg)` }}><Poster movie={movie} rounded="rounded-2xl" /></div>)}</div>)}</div> : loading ? <div className="flex justify-center gap-4 pt-12">{Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton h-56 w-36 shrink-0 rounded-2xl" />)}</div> : null}
      </div>
    </section>
  )
}
