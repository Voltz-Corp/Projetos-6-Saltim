import { AnimatePresence, motion } from 'motion/react';

export function TruckLoading({ show }: { show: boolean }) {
  return (
    <AnimatePresence mode="wait">
      {show && (
        <motion.div
          className="fixed inset-0 z-[9998] flex h-screen w-screen items-center justify-center overflow-hidden bg-[#232323] text-white"
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          style={{ backfaceVisibility: 'hidden', transform: 'translateZ(0)' }}
        >
          <div className="relative h-44 w-screen overflow-hidden">
            <motion.div
              className="absolute left-1/2 top-10 h-24 w-56"
              animate={{ x: ['-40vw', '58vw'] }}
              transition={{
                duration: 2.15,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              <motion.div
                className="absolute left-0 top-5 h-16 w-32 rounded-xl border-4 border-brand-600 bg-saltim-cream shadow-[0_12px_34px_rgba(0,0,0,0.22)]"
                animate={{ y: [0, 2, 0] }}
                transition={{ duration: 0.48, repeat: Infinity }}
              />
              <motion.div
                className="absolute left-28 top-9 h-12 w-16 rounded-r-2xl border-4 border-brand-600 bg-brand-600"
                animate={{ y: [0, 2, 0] }}
                transition={{ duration: 0.48, repeat: Infinity }}
              />
              <div className="absolute left-[150px] top-12 h-5 w-5 rounded-sm bg-saltim-blue/90" />
              <div className="absolute left-5 top-2 h-5 w-7 rotate-[-8deg] rounded border-2 border-saltim-green bg-saltim-green/80" />
              <div className="absolute left-16 top-1 h-6 w-7 rotate-[7deg] rounded border-2 border-brand-600 bg-brand-50" />
              {[35, 151].map((left) => (
                <motion.div
                  key={left}
                  className="absolute top-[72px] size-9 rounded-full border-4 border-stone-700 bg-[#232323]"
                  style={{ left }}
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 0.7,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                >
                  <span className="absolute left-1/2 top-1/2 h-1 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-600" />
                  <span className="absolute left-1/2 top-1/2 h-6 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-600" />
                </motion.div>
              ))}
              {[0, 1, 2].map((index) => (
                <motion.span
                  key={index}
                  className="absolute top-[80px] h-1 rounded-full bg-white/50"
                  style={{ left: -8 - index * 18, width: 18 + index * 8 }}
                  animate={{ opacity: [0, 1, 0], x: [8, -18] }}
                  transition={{
                    duration: 0.58,
                    delay: index * 0.1,
                    repeat: Infinity,
                  }}
                />
              ))}
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
