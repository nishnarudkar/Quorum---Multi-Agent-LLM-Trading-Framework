'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import ThemeProvider from '@/components/ThemeProvider';

export default function AppShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isLandingPage = pathname === '/';

    return (
        <ThemeProvider>
            {!isLandingPage && <Sidebar />}
            <main className={isLandingPage ? "" : "main-content"}>
                {children}
            </main>
        </ThemeProvider>
    );
}
