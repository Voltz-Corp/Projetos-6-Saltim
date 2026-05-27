import { AnimatePresence, motion } from 'motion/react';

export function CoffeeLoading({ show }: { show: boolean }) {
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
          <motion.div
            className="grid place-items-center"
            exit={{ y: -96, opacity: 0 }}
            transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="relative h-32 w-36">
              <motion.div
                className="absolute left-8 top-12 h-14 w-20 rounded-b-2xl rounded-t-md border-4 border-brand-600 bg-saltim-cream"
                animate={{ y: [0, 3, 0] }}
                transition={{ duration: 0.7, repeat: Infinity }}
              >
                <div className="absolute left-[75px] top-[10px] top-16 h-8 w-6 rounded-r-full border-4 border-brand-600 border-l-0" />
              </motion.div>
              {/* <motion.div
                className="absolute left-5 top-0 h-10 w-24 rounded-full border border-brand-200/30"
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}
              >
                <span className="absolute left-3 top-4 size-2 rounded-full bg-brand-600" />
                <span className="absolute left-11 top-1 size-2 rounded-full bg-saltim-blue" />
                <span className="absolute right-3 top-5 size-2 rounded-full bg-saltim-green" />
              </motion.div> */}
              {[0, 1, 2].map((index) => (
                <motion.span
                  key={index}
                  className="absolute top-6 h-9 w-1 rounded-full bg-white/60"
                  style={{ left: 52 + index * 16 }}
                  animate={{ y: [-2, -18], opacity: [0, 1, 0] }}
                  transition={{
                    duration: 1.4,
                    delay: index * 0.2,
                    repeat: Infinity,
                  }}
                />
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
