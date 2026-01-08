import { Suspense } from "react";
import Link from "next/link";

import { Loader2 } from "lucide-react";

import { LoginForm } from "../../_components/login-form";
import { GoogleButton } from "../../_components/social-auth/google-button";
import { APP_CONFIG } from "@/config/app-config";

export default function LoginV1() {
  return (
    <div className="flex h-dvh">
      <div className="hidden bg-primary lg:block lg:w-1/3">
        <div className="flex h-full flex-col items-center justify-center p-12 text-center">
          <div className="space-y-6">
            <div className="space-y-1">
              <h2 className="font-semibold text-2xl text-primary-foreground">{APP_CONFIG.name}</h2>
              <p className="text-sm text-primary-foreground/70">x Prodius Enterprise</p>
            </div>
            <div className="space-y-2">
              <h1 className="font-light text-5xl text-primary-foreground">Hello again</h1>
              <p className="text-primary-foreground/80 text-xl">Login to continue</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex w-full items-center justify-center bg-background p-8 lg:w-2/3">
        <div className="w-full max-w-md space-y-10 py-24 lg:py-32">
          <div className="space-y-4 text-center">
            <div className="font-medium tracking-tight">Login</div>
            <div className="mx-auto max-w-xl text-muted-foreground">
              Welcome back. Enter your email and password, let&apos;s hope you remember them this time.
            </div>
          </div>
          <div className="space-y-4">
            <Suspense fallback={<div className="flex justify-center py-4"><Loader2 className="h-6 w-6 animate-spin" /></div>}>
              <LoginForm />
            </Suspense>
            <GoogleButton className="w-full" variant="outline" />
            <p className="text-center text-muted-foreground text-xs">
              Don&apos;t have an account?{" "}
              <Link prefetch={false} href="register" className="text-primary">
                Register
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
