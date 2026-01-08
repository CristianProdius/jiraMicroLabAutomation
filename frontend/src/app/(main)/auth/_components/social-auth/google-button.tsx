"use client";

import { siGoogle } from "simple-icons";
import { toast } from "sonner";

import { SimpleIcon } from "@/components/simple-icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function GoogleButton({ className, ...props }: React.ComponentProps<typeof Button>) {
  const handleClick = () => {
    toast.info("Google authentication is not yet configured. Please use email/password.");
  };

  return (
    <Button
      type="button"
      variant="secondary"
      className={cn(className)}
      onClick={handleClick}
      {...props}
    >
      <SimpleIcon icon={siGoogle} className="size-4" />
      Continue with Google
    </Button>
  );
}
